"""Wraps the Claude Agent SDK to run a memory sub-agent.

The sub-agent gets:
  - A composed system prompt (base + task-specific + operator-context)
  - In-process MCP tools wrapping our `Store` primitives
  - A short instruction from the main agent

It returns the final assistant text — the synthesis the main agent sees.
"""

from __future__ import annotations

import asyncio
from importlib.resources import files
from pathlib import Path
from typing import Any

from memory_graph.embed.base import Embedder
from memory_graph.orchestration.operator import read_operator_context
from memory_graph.primitives import Store
from memory_graph.storage import Edge

# Default Agent SDK model. We pick Sonnet — cheap and fast enough for the
# sub-agent's work. Bumped to Opus for compact() since that's heavier.
DEFAULT_MODEL = "claude-sonnet-4-6"
COMPACT_MODEL = "claude-opus-4-7"

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


def build_sdk_tools(store: Store) -> list[Any]:
    """Build in-process SDK tool wrappers over `store`.

    Each returns a JSON-serializable dict that the SDK forwards as the
    tool's result. Tool naming matches `DEFAULT_TOOL_NAMES` so the
    `allowed_tools` filter is straightforward.
    """
    from claude_agent_sdk import tool  # local import: SDK is optional

    @tool(
        "search",
        "Semantic top-k over the memory graph. Returns id+summary+kind+score.",
        {"query": str, "k": int, "kind": str, "status": str},
    )
    async def t_search(args: dict[str, Any]) -> dict[str, Any]:
        hits = store.search(
            args["query"],
            k=int(args.get("k", 10)),
            kind=args.get("kind"),
            status=args.get("status"),
        )
        return {"content": [{"type": "text", "text": _json(hits)}]}

    @tool(
        "get",
        "Fetch a single note (body, edges, tags, anchors).",
        {"note_id": str},
    )
    async def t_get(args: dict[str, Any]) -> dict[str, Any]:
        note = store.get(args["note_id"])
        payload = None if note is None else _note_dict(note)
        return {"content": [{"type": "text", "text": _json(payload)}]}

    @tool(
        "neighbors",
        "Walk the graph from a node along edge types, up to N hops.",
        {"note_id": str, "types": list, "depth": int, "direction": str},
    )
    async def t_neighbors(args: dict[str, Any]) -> dict[str, Any]:
        out = store.neighbors(
            args["note_id"],
            types=args.get("types"),
            depth=int(args.get("depth", 1)),
            direction=args.get("direction", "out"),
        )
        return {"content": [{"type": "text", "text": _json(out)}]}

    @tool(
        "capture",
        "Write a single note. Returns id + duplicate flags.",
        {
            "title": str, "summary": str, "body": str, "kind": str,
            "status": str, "tags": list, "edges": list,
            "happened_at": int, "last_verified_at": int, "confidence": float,
        },
    )
    async def t_capture(args: dict[str, Any]) -> dict[str, Any]:
        edges = [
            Edge(to_id=e["to"], type=e["type"], weight=float(e.get("weight", 1.0)))
            for e in (args.get("edges") or [])
        ]
        result = store.capture(
            title=args["title"], summary=args["summary"], body=args["body"],
            kind=args["kind"],
            status=args.get("status", "active"),
            tags=args.get("tags") or [],
            edges=edges,
            happened_at=args.get("happened_at"),
            last_verified_at=args.get("last_verified_at"),
            confidence=float(args.get("confidence", 1.0)),
        )
        return {"content": [{"type": "text", "text": _json(result)}]}

    @tool(
        "capture_batch",
        "Write many notes atomically. Items may use '@1','@2' placeholder ids.",
        {"notes": list},
    )
    async def t_capture_batch(args: dict[str, Any]) -> dict[str, Any]:
        result = store.capture_batch(args["notes"])
        return {"content": [{"type": "text", "text": _json(result)}]}

    @tool(
        "link",
        "Add (or replace) a typed edge between two notes.",
        {"from_id": str, "to_id": str, "type": str, "weight": float},
    )
    async def t_link(args: dict[str, Any]) -> dict[str, Any]:
        store.link(
            args["from_id"], args["to_id"], args["type"],
            weight=float(args.get("weight", 1.0)),
        )
        return {"content": [{"type": "text", "text": "ok"}]}

    @tool(
        "unlink",
        "Remove a typed edge between two notes.",
        {"from_id": str, "to_id": str, "type": str},
    )
    async def t_unlink(args: dict[str, Any]) -> dict[str, Any]:
        store.unlink(args["from_id"], args["to_id"], args["type"])
        return {"content": [{"type": "text", "text": "ok"}]}

    @tool(
        "supersede",
        "Mark old_id as superseded by new_id; adds a 'supersedes' edge.",
        {"old_id": str, "new_id": str, "reason": str},
    )
    async def t_supersede(args: dict[str, Any]) -> dict[str, Any]:
        store.supersede(
            old_id=args["old_id"],
            new_id=args["new_id"],
            reason=args.get("reason", ""),
        )
        return {"content": [{"type": "text", "text": "ok"}]}

    @tool(
        "mark",
        "Change a note's status (e.g. 'disputed', 'disproven', 'stale').",
        {"note_id": str, "status": str},
    )
    async def t_mark(args: dict[str, Any]) -> dict[str, Any]:
        store.mark(args["note_id"], args["status"])
        return {"content": [{"type": "text", "text": "ok"}]}

    @tool(
        "status",
        "Counts by kind / status / edge type, plus embedding model info.",
        {},
    )
    async def t_status(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": _json(store.status())}]}

    return [
        t_search, t_get, t_neighbors,
        t_capture, t_capture_batch,
        t_link, t_unlink, t_supersede, t_mark, t_status,
    ]


async def run_subagent(
    *,
    task: str,
    user_message: str,
    store: Store,
    model: str = DEFAULT_MODEL,
    allowed_tools: tuple[str, ...] = DEFAULT_TOOL_NAMES,
) -> str:
    """Run the memory sub-agent for `task` and return its final text.

    `task` selects the prompt template (`remember`, `retrieve`, `compact`).
    The sub-agent gets in-process tools over `store` and a system prompt
    composed from base + task + operator-context.
    """
    from claude_agent_sdk import (  # local import: SDK is optional
        AssistantMessage,
        ClaudeAgentOptions,
        create_sdk_mcp_server,
        query,
    )

    system_prompt = compose_system_prompt(task, store.root)
    server = create_sdk_mcp_server(name="memory", tools=build_sdk_tools(store))
    options = ClaudeAgentOptions(
        model=model,
        system_prompt=system_prompt,
        mcp_servers={"memory": server},
        allowed_tools=[f"mcp__memory__{name}" for name in allowed_tools],
    )

    chunks: list[str] = []
    async for message in query(prompt=user_message, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                text = getattr(block, "text", None)
                if text:
                    chunks.append(text)
    return "\n".join(chunks).strip()


def run_subagent_sync(**kwargs: Any) -> str:
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
