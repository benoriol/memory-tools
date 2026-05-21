"""Wraps the Claude Agent SDK to run a memory sub-agent.

The sub-agent gets:
  - A composed system prompt (base + task-specific + operator-context)
  - In-process MCP tools wrapping our `Store` primitives
  - A short instruction from the main agent

`run_subagent()` returns a `SubAgentResult` carrying the synthesis text
PLUS usage / cost / stop-reason metadata extracted from the SDK's
`ResultMessage`. Callers that just want the synthesis use `.text`;
callers that want to surface cost (e.g. the MCP tool responses)
forward the metadata.

On `ResultMessage.is_error` we raise — silent empty returns are the
historical failure mode the verifier flagged.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any

from memory_graph.embed.base import Embedder
from memory_graph.orchestration.operator import read_operator_context
from memory_graph.primitives import Store
from memory_graph.storage import Edge

# Sub-agent model selection — one model per operation.
#
# remember (writes): Sonnet at low effort. Haiku was tempting for speed
#   but consistently ignored the dup-flag → supersede flow (wrote
#   duplicates instead of acknowledging them). Sonnet-low honors the
#   multi-step write/link/supersede instructions reliably.
#
# retrieve (reads): Haiku at low effort. Read-only graph navigation; no
#   write discipline needed. Benchmarked at 0.883 overall, 1.00 on the
#   hard tier (multi-hop walks) — equal quality to Sonnet at ~3× the
#   speed.
#
# compact: Opus at medium effort. Cross-cluster reasoning across many
#   notes — the heaviest of the three operations.
#
# `effort` is the Agent SDK's extended-thinking budget knob:
#   "low"    — minimal thinking, fastest
#   "medium" — balanced (default for agentic tasks if unspecified)
#   "high" / "xhigh" / "max" — progressively more thinking
REMEMBER_MODEL  = "claude-sonnet-4-6"
REMEMBER_EFFORT = "low"

RETRIEVE_MODEL  = "claude-haiku-4-5-20251001"
RETRIEVE_EFFORT = "low"

COMPACT_MODEL   = "claude-opus-4-7"
COMPACT_EFFORT  = "medium"

# `run_subagent` defaults to the remember configuration if a caller
# doesn't override — it's the strictest of the three (write discipline),
# so it's the safest fallback.
DEFAULT_MODEL   = REMEMBER_MODEL
DEFAULT_EFFORT  = REMEMBER_EFFORT

# Hard ceiling on sub-agent tool-use round trips. Without this a confused
# sub-agent can spin until it hits the model's context window, burning
# tokens and time silently. Generous enough for normal multi-batch
# remember/retrieve work; compact runs across more nodes and warrants more.
DEFAULT_MAX_TURNS = 30
COMPACT_MAX_TURNS = 50

# Allowed tools when the sub-agent runs. Memory primitives only — no
# Read/Write/Bash, no network. The sub-agent's job is graph navigation,
# not filesystem editing.
DEFAULT_TOOL_NAMES = (
    "search",
    "get",
    "neighbors",
    "capture",
    "capture_batch",
    "link",
    "unlink",
    "supersede",
    "mark",
    "status",
)


def load_prompt(name: str) -> str:
    """Load a packaged prompt template by base name (e.g. 'remember')."""
    return files("memory_graph.prompts").joinpath(f"{name}.md").read_text()


def compose_system_prompt(task: str, store_root: str | Path) -> str:
    """Stitch the system prompt: base + task-specific + operator-context."""
    base = load_prompt("system")
    task_specific = load_prompt(task)
    operator = read_operator_context(store_root)
    return (
        f"{base}\n\n---\n\n{task_specific}\n\n---\n\n"
        f"# Operator context (current snapshot)\n\n{operator}"
    )


def _ok(value: Any) -> dict[str, Any]:
    """SDK tool 'success' envelope."""
    return {"content": [{"type": "text", "text": _json(value)}]}


def _err(exc: BaseException) -> dict[str, Any]:
    """SDK tool 'error' envelope. The sub-agent sees isError=True and the
    exception text so it can react instead of treating the call as silent
    success (which is what previously let it hallucinate writes that never
    landed).
    """
    return {
        "content": [
            {
                "type": "text",
                "text": _json(
                    {"error": f"{type(exc).__name__}: {exc}"}
                ),
            }
        ],
        "isError": True,
    }


def build_sdk_tools(store: Store) -> list[Any]:
    """Build in-process SDK tool wrappers over `store`.

    Each returns a JSON-serializable dict that the SDK forwards as the
    tool's result. Tool naming matches `DEFAULT_TOOL_NAMES` so the
    `allowed_tools` filter is straightforward.

    Every wrapper traps exceptions and returns an isError envelope so the
    sub-agent always sees a clear success/failure signal — never a silent
    crash that gets misinterpreted as success.
    """
    from claude_agent_sdk import tool  # local import: SDK is optional

    @tool(
        "search",
        "Semantic top-k over the memory graph. Returns id+summary+kind+score.",
        {"query": str, "k": int, "kind": str, "status": str},
    )
    async def t_search(args: dict[str, Any]) -> dict[str, Any]:
        try:
            hits = store.search(
                args["query"],
                k=int(args.get("k", 10)),
                kind=args.get("kind"),
                status=args.get("status"),
            )
            return _ok(hits)
        except Exception as exc:
            return _err(exc)

    @tool(
        "get",
        "Fetch a single note (body, edges, tags, anchors).",
        {"note_id": str},
    )
    async def t_get(args: dict[str, Any]) -> dict[str, Any]:
        try:
            note = store.get(args["note_id"])
            return _ok(None if note is None else _note_dict(note))
        except Exception as exc:
            return _err(exc)

    @tool(
        "neighbors",
        "Walk the graph from a node along edge types, up to N hops.",
        {"note_id": str, "types": list, "depth": int, "direction": str},
    )
    async def t_neighbors(args: dict[str, Any]) -> dict[str, Any]:
        try:
            out = store.neighbors(
                args["note_id"],
                types=args.get("types"),
                depth=int(args.get("depth", 1)),
                direction=args.get("direction", "out"),
            )
            return _ok(out)
        except Exception as exc:
            return _err(exc)

    @tool(
        "capture",
        "Write a single note. Returns id + duplicate flags. "
        "`short_label` is a <=5-word label used by the graph viz; "
        "always provide one.",
        {
            "title": str, "short_label": str, "summary": str, "body": str,
            "kind": str, "status": str, "tags": list, "edges": list,
            "happened_at": int, "last_verified_at": int, "confidence": float,
        },
    )
    async def t_capture(args: dict[str, Any]) -> dict[str, Any]:
        try:
            edges = [
                Edge(to_id=e["to"], type=e["type"], weight=float(e.get("weight", 1.0)))
                for e in (args.get("edges") or [])
            ]
            result = store.capture(
                title=args["title"], summary=args["summary"], body=args["body"],
                kind=args["kind"],
                status=args.get("status", "active"),
                short_label=args.get("short_label"),
                tags=args.get("tags") or [],
                edges=edges,
                happened_at=args.get("happened_at"),
                last_verified_at=args.get("last_verified_at"),
                confidence=float(args.get("confidence", 1.0)),
            )
            return _ok(result)
        except Exception as exc:
            return _err(exc)

    @tool(
        "capture_batch",
        "Write many notes atomically. Items may use '@1','@2' placeholder ids.",
        {"notes": list},
    )
    async def t_capture_batch(args: dict[str, Any]) -> dict[str, Any]:
        try:
            return _ok(store.capture_batch(args["notes"]))
        except Exception as exc:
            return _err(exc)

    @tool(
        "link",
        "Add (or replace) a typed edge between two notes.",
        {"from_id": str, "to_id": str, "type": str, "weight": float},
    )
    async def t_link(args: dict[str, Any]) -> dict[str, Any]:
        try:
            store.link(
                args["from_id"], args["to_id"], args["type"],
                weight=float(args.get("weight", 1.0)),
            )
            return _ok("ok")
        except Exception as exc:
            return _err(exc)

    @tool(
        "unlink",
        "Remove a typed edge between two notes.",
        {"from_id": str, "to_id": str, "type": str},
    )
    async def t_unlink(args: dict[str, Any]) -> dict[str, Any]:
        try:
            store.unlink(args["from_id"], args["to_id"], args["type"])
            return _ok("ok")
        except Exception as exc:
            return _err(exc)

    @tool(
        "supersede",
        "Mark old_id as superseded by new_id; adds a 'supersedes' edge.",
        {"old_id": str, "new_id": str, "reason": str},
    )
    async def t_supersede(args: dict[str, Any]) -> dict[str, Any]:
        try:
            store.supersede(
                old_id=args["old_id"],
                new_id=args["new_id"],
                reason=args.get("reason", ""),
            )
            return _ok("ok")
        except Exception as exc:
            return _err(exc)

    @tool(
        "mark",
        "Change a note's status (e.g. 'disputed', 'disproven', 'stale').",
        {"note_id": str, "status": str},
    )
    async def t_mark(args: dict[str, Any]) -> dict[str, Any]:
        try:
            store.mark(args["note_id"], args["status"])
            return _ok("ok")
        except Exception as exc:
            return _err(exc)

    @tool(
        "status",
        "Counts by kind / status / edge type, plus embedding model info.",
        {},
    )
    async def t_status(args: dict[str, Any]) -> dict[str, Any]:
        try:
            return _ok(store.status())
        except Exception as exc:
            return _err(exc)

    return [
        t_search, t_get, t_neighbors,
        t_capture, t_capture_batch,
        t_link, t_unlink, t_supersede, t_mark, t_status,
    ]


@dataclass(slots=True)
class SubAgentResult:
    """What `run_subagent` returns. Carries the synthesis text plus the
    metadata callers need to surface cost / usage / stop reason.
    """

    text: str
    usage: dict[str, Any] = field(default_factory=dict)
    model_usage: dict[str, Any] = field(default_factory=dict)
    total_cost_usd: float | None = None
    stop_reason: str | None = None


class SubAgentError(RuntimeError):
    """Raised when the SDK's ResultMessage signals is_error=True. Carries
    the stop_reason and any structured errors back to the caller so MCP
    tool responses can surface a proper failure instead of returning an
    empty synthesis.
    """

    def __init__(self, message: str, *, stop_reason: str | None = None,
                 errors: list[str] | None = None):
        super().__init__(message)
        self.stop_reason = stop_reason
        self.errors = errors or []


async def run_subagent(
    *,
    task: str,
    user_message: str,
    store: Store,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EFFORT,
    allowed_tools: tuple[str, ...] = DEFAULT_TOOL_NAMES,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> SubAgentResult:
    """Run the memory sub-agent for `task` and return text + usage metadata.

    `task` selects the prompt template (`remember`, `retrieve`, `compact`).
    The sub-agent gets in-process tools over `store` and a system prompt
    composed from base + task + operator-context.

    `effort` is the Agent SDK's thinking budget (low|medium|high|xhigh|max).
    Default is "low" — memory ops are mostly mechanical and don't benefit
    much from extended thinking; compact bumps to "medium".

    `max_turns` caps tool-use round trips; raises (via the SDK) if hit.

    Raises:
      SubAgentError: if the SDK reports `ResultMessage.is_error=True`.
        Empty synthesis is otherwise indistinguishable from a successful
        write-nothing run; we convert SDK-level failures into exceptions
        so the MCP tool layer can return a real error to the caller.
    """
    from claude_agent_sdk import (  # local import: SDK is optional
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        create_sdk_mcp_server,
        query,
    )

    system_prompt = compose_system_prompt(task, store.root)
    server = create_sdk_mcp_server(name="memory", tools=build_sdk_tools(store))
    options = ClaudeAgentOptions(
        model=model,
        effort=effort,
        system_prompt=system_prompt,
        mcp_servers={"memory": server},
        allowed_tools=[f"mcp__memory__{name}" for name in allowed_tools],
        # Headless sub-agent inside FastMCP's event loop: prompting would
        # hang stdio forever. The sub-agent's tool surface is the closed
        # DEFAULT_TOOL_NAMES list (no fs/network), so bypass is safe.
        permission_mode="bypassPermissions",
        max_turns=max_turns,
    )

    chunks: list[str] = []
    last_result: ResultMessage | None = None
    async for message in query(prompt=user_message, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                text = getattr(block, "text", None)
                if text:
                    chunks.append(text)
        elif isinstance(message, ResultMessage):
            last_result = message

    text = "\n".join(chunks).strip()
    usage = dict(getattr(last_result, "usage", None) or {}) if last_result else {}
    model_usage = dict(getattr(last_result, "model_usage", None) or {}) if last_result else {}
    total_cost_usd = getattr(last_result, "total_cost_usd", None) if last_result else None
    stop_reason = getattr(last_result, "stop_reason", None) if last_result else None

    if last_result is not None and bool(getattr(last_result, "is_error", False)):
        errors = list(getattr(last_result, "errors", None) or [])
        raise SubAgentError(
            f"sub-agent failed (stop_reason={stop_reason!r}): {errors or '<no detail>'}",
            stop_reason=stop_reason,
            errors=errors,
        )

    return SubAgentResult(
        text=text,
        usage=usage,
        model_usage=model_usage,
        total_cost_usd=total_cost_usd,
        stop_reason=stop_reason,
    )


def run_subagent_sync(**kwargs: Any) -> SubAgentResult:
    """Synchronous wrapper for callers NOT already inside an event loop.

    The MCP server's tools run inside FastMCP's event loop, so they must
    `await run_subagent(...)` directly. This wrapper is only safe for
    truly sync contexts — the CLI digest command, mostly.
    """
    return asyncio.run(run_subagent(**kwargs))


# -- helpers ----------------------------------------------------------------


def _note_dict(note) -> dict[str, Any]:
    return {
        "id": note.id,
        "title": note.title,
        "short_label": note.short_label,
        "summary": note.summary,
        "body": note.body,
        "kind": note.kind,
        "status": note.status,
        "created_at": note.created_at,
        "updated_at": note.updated_at,
        "happened_at": note.happened_at,
        "last_verified_at": note.last_verified_at,
        "confidence": note.confidence,
        "tags": list(note.tags),
        "edges": [
            {"to": e.to_id, "type": e.type, "weight": e.weight} for e in note.edges
        ],
        "anchors": [
            {"path": a.path, "pattern": a.pattern, "commit": a.commit_sha}
            for a in note.anchors
        ],
    }


def _json(value: Any) -> str:
    import json
    return json.dumps(value, default=str)


# Keep linter happy: Embedder is referenced in type hints elsewhere in the
# package; importing it here documents that runner.py is the consumer.
_ = Embedder
