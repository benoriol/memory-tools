"""B7: Cross-session architectural recall.

PHASE 1: agent investigates a synthetic 30-module codebase. The structure
has many specific architectural details (singletons, plugin contracts,
config hierarchies, event flows). Agent is told to learn it thoroughly.

BETWEEN PHASES: ALL source code is deleted. Only .memory-graph (if any)
remains. So phase 2 has no on-disk source to consult.

PHASE 2: agent must answer 12 specific architectural questions.

no_memory should fail catastrophically (no source, no memory). With memory,
performance depends on how well it captured the structure.

This design exists to:
  (a) confirm that cross-session multi-phase IS the regime where memory's
      necessity becomes clear, and
  (b) probe how many distinct facts the memory graph can carry per phase.
"""

from __future__ import annotations

import asyncio
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Apply limits before imports.
RAM_BYTES_CAP = 32 * 1024 ** 3
CPU_CORES_CAP = 64


def _apply_limits() -> None:
    try:
        resource.setrlimit(resource.RLIMIT_AS, (RAM_BYTES_CAP, RAM_BYTES_CAP))
    except (ValueError, OSError) as exc:
        print(f"[limits] RLIMIT_AS not applied: {exc}", file=sys.stderr)
    try:
        cpus = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, set(cpus[:CPU_CORES_CAP]))
    except (AttributeError, OSError) as exc:
        print(f"[limits] sched_setaffinity not applied: {exc}", file=sys.stderr)
    os.environ["CUDA_VISIBLE_DEVICES"] = ""


_apply_limits()


REPO_ROOT = Path(__file__).resolve().parents[3]
PIPX_MEMORY_GRAPH = Path.home() / ".local" / "bin" / "memory-graph"
RESULTS_DIR = REPO_ROOT / "demos" / "eval" / "results" / "lab"
WORK_BASE = Path("/tmp/lab-bench")

# 30 architectural facts: each is a specific question with a specific
# string answer that should appear in the agent's phase-1 read of the code.
# We seed these into the generated codebase as comments or constants.

FACTS = [
    {"q": "Which module owns the singleton registry?", "ans": "core.registry"},
    {"q": "What is the magic byte at the start of the binary format?", "ans": "0x7f"},
    {"q": "What is the default cache TTL in seconds?", "ans": "3600"},
    {"q": "Which plugin contract has 4 required methods?", "ans": "TransformPlugin"},
    {"q": "What environment variable overrides the data root?", "ans": "DATAFLOW_HOME"},
    {"q": "Which class implements the visitor pattern over the AST?", "ans": "AstWalker"},
    {"q": "What is the maximum retry count for failed jobs?", "ans": "5"},
    {"q": "Which port does the metrics endpoint bind to by default?", "ans": "9342"},
    {"q": "What checksum algorithm is used for chunk verification?", "ans": "blake3"},
    {"q": "Which event triggers a cache invalidation flush?", "ans": "ConfigReloaded"},
    {"q": "What is the name of the exception raised on quota exhaustion?", "ans": "QuotaExceeded"},
    {"q": "Which module is responsible for connection pooling?", "ans": "transport.pool"},
    {"q": "How many priority levels does the scheduler support?", "ans": "7"},
    {"q": "What is the file extension for the on-disk index format?", "ans": ".idx2"},
    {"q": "Which class provides the audit log abstraction?", "ans": "AuditTrail"},
    {"q": "What is the maximum payload size in bytes?", "ans": "1048576"},
    {"q": "Which module hosts the dependency injection container?", "ans": "core.di"},
    {"q": "What is the default poll interval for the watcher in milliseconds?", "ans": "250"},
    {"q": "Which protocol version is documented as current?", "ans": "v3.2"},
    {"q": "What is the codename of the experimental query planner?", "ans": "Vermeer"},
    {"q": "Which method on the Storage class handles compaction?", "ans": "compact_tier"},
    {"q": "What is the rate-limit window size in seconds?", "ans": "120"},
    {"q": "Which two modules share the same lock manager?", "ans": "storage and indexer"},
    {"q": "What is the magic constant for the bloom filter seed?", "ans": "0xC0FFEE"},
    {"q": "Which class implements the circuit breaker for external calls?", "ans": "OutboundBreaker"},
    {"q": "What is the default thread pool size?", "ans": "16"},
    {"q": "Which module owns the metrics aggregation buffer?", "ans": "telemetry.buffer"},
    {"q": "What is the schema version of the persisted catalog?", "ans": "schema_v4"},
    {"q": "Which encoding is used for inter-process messages?", "ans": "msgpack"},
    {"q": "Which class wraps the connection state machine?", "ans": "ConnectionFsm"},
]


def _generate_codebase(workdir: Path) -> None:
    """Generate 30 small modules. Each module contains 1-2 architectural facts
    seeded as docstrings, comments, or named constants. Plus filler code so
    facts aren't in trivially obvious positions.
    """
    workdir.mkdir(parents=True, exist_ok=True)

    # Each fact gets seeded into a specific module file. We'll create 30 modules.
    # To make the codebase more codebase-y, each module also has a Class and
    # a few methods with realistic-looking but irrelevant code.

    for i, fact in enumerate(FACTS):
        mod_name = f"module_{i:02d}"
        body = f'''"""Module {mod_name}.

Part of the dataflow project. This module participates in the broader
architecture in ways documented in adjacent files. Note: {fact["q"].lower().rstrip("?")} — {fact["ans"]}.
"""

from typing import Any


class Component_{i:02d}:
    """A component class with some methods."""

    CONFIG_KEY = "component.{i:02d}.enabled"

    def __init__(self, config: dict) -> None:
        self.config = config
        self._state = {{}}

    def initialize(self) -> None:
        # No-op placeholder; real initialization in subclass.
        pass

    def step(self, payload: Any) -> Any:
        self._state["last_payload"] = payload
        return payload

    def shutdown(self) -> None:
        self._state.clear()


def factory(config: dict) -> Component_{i:02d}:
    return Component_{i:02d}(config)
'''
        (workdir / f"{mod_name}.py").write_text(body)

    # Also add a top-level README-like architecture doc, just to give the
    # agent something to chew on. Don't restate facts — just give context.
    (workdir / "ARCHITECTURE.md").write_text(
        "# Dataflow architecture\n\n"
        "30 modules form the dataflow runtime. Each module exposes a Component\n"
        "class plus a factory. Read the individual modules to understand their\n"
        "specific responsibilities and any architectural constants they declare.\n"
    )


PHASE1_PROMPT = """\
You are doing an architectural audit of the `dataflow` project in this
directory. There are 30 modules (module_00.py through module_29.py) plus
an ARCHITECTURE.md.

Each module's docstring includes a specific architectural fact about the
project (a magic constant, a default value, a class name responsible for
some role, an env var name, etc.).

YOUR TASK: read every module and DOCUMENT thoroughly each architectural
fact. After this phase, ALL SOURCE FILES WILL BE DELETED — your only
record of these facts in the next phase will be whatever you preserve
via available memory tools.

If you have tools whose names start with `mcp__memory-graph__`, USE THEM
NOW to capture each fact as a separate note. Otherwise, you will not be
able to answer questions in the next phase.

Read all 30 modules thoroughly. Capture every architectural fact you find.
"""


PHASE2_PROMPT = """\
Answer the following architectural questions about the dataflow project.

The source code has been DELETED. Your only source of information is
whatever you captured during the prior investigation phase. If you have
tools whose names start with `mcp__memory-graph__`, CALL THEM NOW (use
memory_retrieve, memory_search, memory_status) to recall the facts.

Output your answers in EXACTLY this format on the last 30 lines:

Q01: <answer>
Q02: <answer>
...
Q30: <answer>

Use the EXACT string that appeared in the code; do not paraphrase.

Questions:
{questions}
"""


async def run_phase(prompt: str, workdir: Path, *, with_memory: bool, max_turns: int = 60) -> dict[str, Any]:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        query,
    )

    allowed = ["Read", "Bash", "Glob", "Grep", "Write", "Edit"]
    mcp_servers: dict[str, Any] = {}
    if with_memory:
        allowed += [
            "mcp__memory-graph__memory_remember",
            "mcp__memory-graph__memory_retrieve",
            "mcp__memory-graph__memory_search",
            "mcp__memory-graph__memory_get",
            "mcp__memory-graph__memory_neighbors",
            "mcp__memory-graph__memory_status",
            "mcp__memory-graph__memory_capture",
            "mcp__memory-graph__memory_capture_batch",
        ]
        mcp_servers["memory-graph"] = {
            "command": str(PIPX_MEMORY_GRAPH),
            "args": ["serve"],
        }

    options = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        effort="low",
        permission_mode="bypassPermissions",
        cwd=str(workdir),
        allowed_tools=allowed,
        mcp_servers=mcp_servers,
        max_turns=max_turns,
    )

    text_chunks: list[str] = []
    last_result = None
    t0 = time.monotonic()
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                t = getattr(block, "text", None)
                if t:
                    text_chunks.append(t)
        elif isinstance(msg, ResultMessage):
            last_result = msg
    usage = dict(getattr(last_result, "usage", None) or {}) if last_result else {}
    cost = getattr(last_result, "total_cost_usd", None) if last_result else None
    return {
        "text": "\n".join(text_chunks).strip(),
        "usage": usage,
        "cost_usd": cost,
        "seconds": round(time.monotonic() - t0, 1),
    }


def grade(text: str, truth: list[dict]) -> dict[str, Any]:
    import re

    field_scores: list[float] = []
    pattern_map: dict[int, str] = {}
    for i, _ in enumerate(truth):
        m = re.search(rf"Q{i + 1:02d}\s*:\s*(.+)", text or "")
        pattern_map[i + 1] = m.group(1).strip() if m else ""
    for i, fact in enumerate(truth):
        got = pattern_map.get(i + 1, "").lower()
        ans = fact["ans"].lower()
        # Be lenient: match if the answer string is contained in the response.
        ok = ans in got or any(tok in got for tok in ans.split() if len(tok) > 3)
        field_scores.append(1.0 if ok else 0.0)
    return {
        "score": round(sum(field_scores) / len(field_scores), 3),
        "hits": int(sum(field_scores)),
        "total": len(field_scores),
        "per_question": pattern_map,
    }


async def run_arm(arm: str, *, seed: int = 0) -> dict[str, Any]:
    ts = time.strftime("%Y%m%d-%H%M%S")
    workdir = WORK_BASE / f"b7-{arm}-{ts}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    _generate_codebase(workdir)

    if arm == "with_memory":
        subprocess.run(
            [str(PIPX_MEMORY_GRAPH), "init"],
            cwd=str(workdir), check=True, capture_output=True,
        )

    print(f"=== B7 ARM: {arm} ===")
    print(f"  workdir: {workdir}")
    print(f"  phase 1 (investigate) ... ", end="", flush=True)
    p1 = await run_phase(PHASE1_PROMPT, workdir, with_memory=(arm == "with_memory"), max_turns=90)
    print(f"{p1['seconds']}s  cost=${p1['cost_usd'] or 0:.4f}")

    # PURGE source files — but keep .memory-graph if present.
    for path in workdir.iterdir():
        if path.name == ".memory-graph":
            continue
        if path.is_file():
            try:
                path.unlink()
            except OSError:
                pass
        elif path.is_dir():
            shutil.rmtree(path)
    print("  all source PURGED from cwd; .memory-graph preserved (if any)")

    questions = "\n".join(f"Q{i + 1:02d}: {f['q']}" for i, f in enumerate(FACTS))
    print("  phase 2 (recall)         ... ", end="", flush=True)
    p2 = await run_phase(
        PHASE2_PROMPT.format(questions=questions),
        workdir,
        with_memory=(arm == "with_memory"),
        max_turns=60,
    )
    print(f"{p2['seconds']}s  cost=${p2['cost_usd'] or 0:.4f}")

    sc = grade(p2["text"], FACTS)
    print(f"  score: {sc['hits']}/{sc['total']}  ({sc['score']:.2%})")
    tail = "\n".join(p2["text"].splitlines()[-20:])
    print(f"  tail:\n---\n{tail}\n---")

    return {
        "arm": arm,
        "score": sc,
        "phase1": {k: v for k, v in p1.items() if k != "text"},
        "phase2": {k: v for k, v in p2.items() if k != "text"},
        "total_cost_usd": (p1.get("cost_usd") or 0) + (p2.get("cost_usd") or 0),
        "total_seconds": round(p1["seconds"] + p2["seconds"], 1),
    }


async def main_async() -> int:
    print("=" * 64)
    print("B7: Cross-session architectural recall (30 facts)")
    print("=" * 64)
    no_mem = await run_arm("no_memory")
    with_mem = await run_arm("with_memory")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "b7_xsession_arch.json").write_text(
        json.dumps({"no_memory": no_mem, "with_memory": with_mem}, indent=2)
    )
    print()
    print("FINAL")
    print(f"  no_memory   {no_mem['score']['hits']}/30  cost=${no_mem['total_cost_usd']:.4f}  time={no_mem['total_seconds']}s")
    print(f"  with_memory {with_mem['score']['hits']}/30  cost=${with_mem['total_cost_usd']:.4f}  time={with_mem['total_seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
