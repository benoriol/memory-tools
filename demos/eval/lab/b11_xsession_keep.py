"""B11: Cross-session recall WITH FILES STILL PRESENT.

This is B7 minus the artificial file deletion. The realistic question:
when a developer comes back tomorrow, the code is still there — but
they don't remember which files they read or what they found. Does the
memory of session-1's findings beat re-navigating the corpus in
session 2?

DIFFERENCES FROM B7:
  1. Files are NOT deleted between phases. Phase 2 has full filesystem
     access just like phase 1 did.
  2. Phase-2 questions are PARAPHRASED — they do not contain the
     vocabulary that was seeded into module docstrings. So grep on the
     question text returns nothing useful; the no_memory agent has to
     read modules to discover relevant content.
  3. Phase 1 and phase 2 are separate query() calls — fresh agents,
     no carry-over of in-context grep history.

Predicted: both arms reach high accuracy (corpus is navigable). The
*interesting* outcome is the cost: with_memory should be much cheaper
in phase 2 because it skips re-investigation.
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


# Each fact has THREE strings:
#   seed_phrase : the wording used in the docstring inside the code
#   question    : a paraphrase of seed_phrase using different vocabulary
#   ans         : the exact answer string that appears as a constant or
#                 identifier in the code

FACTS = [
    {"seed_phrase": "the central object holding all global singletons",
     "question": "Which module owns the singleton registry?",
     "ans": "core.registry"},
    {"seed_phrase": "the first byte of every serialized frame",
     "question": "What is the magic byte at the start of the binary format?",
     "ans": "0x7f"},
    {"seed_phrase": "how long cached entries stay valid in seconds",
     "question": "What is the default cache TTL in seconds?",
     "ans": "3600"},
    {"seed_phrase": "the contract that downstream transformers implement",
     "question": "Which plugin contract has 4 required methods?",
     "ans": "TransformPlugin"},
    {"seed_phrase": "the variable a user sets to relocate the data directory",
     "question": "What environment variable overrides the data root?",
     "ans": "DATAFLOW_HOME"},
    {"seed_phrase": "the traversal helper for syntax trees",
     "question": "Which class implements the visitor pattern over the AST?",
     "ans": "AstWalker"},
    {"seed_phrase": "the cap on how many times we retry a broken job",
     "question": "What is the maximum retry count for failed jobs?",
     "ans": "5"},
    {"seed_phrase": "the TCP listener for Prometheus scrapes",
     "question": "Which port does the metrics endpoint bind to by default?",
     "ans": "9342"},
    {"seed_phrase": "the hash used to validate each storage chunk",
     "question": "What checksum algorithm is used for chunk verification?",
     "ans": "blake3"},
    {"seed_phrase": "the signal that forces all caches to drop their entries",
     "question": "Which event triggers a cache invalidation flush?",
     "ans": "ConfigReloaded"},
    {"seed_phrase": "the error thrown when a tenant hits their usage cap",
     "question": "What is the name of the exception raised on quota exhaustion?",
     "ans": "QuotaExceeded"},
    {"seed_phrase": "the layer that manages reusable network sockets",
     "question": "Which module is responsible for connection pooling?",
     "ans": "transport.pool"},
    {"seed_phrase": "how many distinct urgency levels the queue accepts",
     "question": "How many priority levels does the scheduler support?",
     "ans": "7"},
    {"seed_phrase": "the suffix written for indexed lookup files",
     "question": "What is the file extension for the on-disk index format?",
     "ans": ".idx2"},
    {"seed_phrase": "the recorder of every administrative action",
     "question": "Which class provides the audit log abstraction?",
     "ans": "AuditTrail"},
    {"seed_phrase": "the upper bound in bytes for any single request body",
     "question": "What is the maximum payload size in bytes?",
     "ans": "1048576"},
    {"seed_phrase": "the registry that wires components together",
     "question": "Which module hosts the dependency injection container?",
     "ans": "core.di"},
    {"seed_phrase": "the delay in ms between filesystem scans",
     "question": "What is the default poll interval for the watcher in milliseconds?",
     "ans": "250"},
    {"seed_phrase": "the wire protocol revision in use today",
     "question": "Which protocol version is documented as current?",
     "ans": "v3.2"},
    {"seed_phrase": "the internal name for the new optimizer",
     "question": "What is the codename of the experimental query planner?",
     "ans": "Vermeer"},
    {"seed_phrase": "the routine that merges old tiered files",
     "question": "Which method on the Storage class handles compaction?",
     "ans": "compact_tier"},
    {"seed_phrase": "the duration of the throttling window in seconds",
     "question": "What is the rate-limit window size in seconds?",
     "ans": "120"},
    {"seed_phrase": "the two components that contend on the same mutex",
     "question": "Which two modules share the same lock manager?",
     "ans": "storage and indexer"},
    {"seed_phrase": "the salt mixed into bloom filter hashes",
     "question": "What is the magic constant for the bloom filter seed?",
     "ans": "0xC0FFEE"},
    {"seed_phrase": "the guard that trips when a remote service misbehaves",
     "question": "Which class implements the circuit breaker for external calls?",
     "ans": "OutboundBreaker"},
    {"seed_phrase": "the worker count for the shared executor",
     "question": "What is the default thread pool size?",
     "ans": "16"},
    {"seed_phrase": "the ring that accumulates measurements before flush",
     "question": "Which module owns the metrics aggregation buffer?",
     "ans": "telemetry.buffer"},
    {"seed_phrase": "the format identifier on the saved catalog file",
     "question": "What is the schema version of the persisted catalog?",
     "ans": "schema_v4"},
    {"seed_phrase": "the serialization used to talk between processes",
     "question": "Which encoding is used for inter-process messages?",
     "ans": "msgpack"},
    {"seed_phrase": "the finite-state machine modeling each socket lifecycle",
     "question": "Which class wraps the connection state machine?",
     "ans": "ConnectionFsm"},
]


def _generate_codebase(workdir: Path) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    for i, fact in enumerate(FACTS):
        mod_name = f"module_{i:02d}"
        body = f'''"""Module {mod_name}.

Part of the dataflow project. Note: {fact["seed_phrase"]} — {fact["ans"]}.
"""

from typing import Any


class Component_{i:02d}:
    """A component class with some methods."""

    CONFIG_KEY = "component.{i:02d}.enabled"

    def __init__(self, config: dict) -> None:
        self.config = config
        self._state = {{}}

    def initialize(self) -> None:
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
    (workdir / "ARCHITECTURE.md").write_text(
        "# Dataflow architecture\n\n"
        "30 modules form the dataflow runtime. Each module exposes a Component\n"
        "class plus a factory. Read individual modules to learn the architectural\n"
        "details documented in their module docstrings.\n"
    )


PHASE1_PROMPT = """\
You are doing an architectural audit of the `dataflow` project in this
directory. There are 30 modules (module_00.py through module_29.py).

Each module's docstring contains a specific architectural fact (a magic
constant, a default value, a class name, an env var, etc.) phrased in
domain language.

YOUR TASK: read every module and DOCUMENT every architectural fact you
find. A different agent will be asked questions about this project
tomorrow — that agent will not see your reading history. The files will
still be on disk, but that agent will have to either re-read everything
or consult notes you leave behind.

If you have tools whose names start with `mcp__memory-graph__`, USE THEM
NOW (memory_capture_batch is ideal) to capture each fact you find as a
note. Use rich, descriptive content — include both the domain phrasing
and the specific value/identifier — so tomorrow's agent can find the
relevant note via semantic search.

Read all 30 modules. Capture every architectural fact.
"""


PHASE2_PROMPT = """\
Answer the following architectural questions about the dataflow project.

The 30 source modules (module_00.py through module_29.py) are still on
disk in the current working directory. You can read them.

But: a prior agent already investigated this codebase. If you have tools
whose names start with `mcp__memory-graph__`, the prior agent's notes
should be in the memory graph — CALL THEM FIRST (memory_search or
memory_retrieve with each question) before falling back to reading
files. The notes were captured with semantic descriptions; semantic
search should find them.

Output your answers in EXACTLY this format on the last 30 lines:

Q01: <answer>
Q02: <answer>
...
Q30: <answer>

Use the EXACT string/identifier that appears in the code (e.g.
"core.registry", "0x7f", "TransformPlugin"); do not paraphrase the
answer itself.

Questions:
{questions}
"""


async def run_phase(
    prompt: str,
    workdir: Path,
    *,
    with_memory: bool,
    max_turns: int = 90,
) -> dict[str, Any]:
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

    pattern_map: dict[int, str] = {}
    for i in range(len(truth)):
        m = re.search(rf"Q{i + 1:02d}\s*:\s*(.+)", text or "")
        pattern_map[i + 1] = m.group(1).strip() if m else ""
    field_scores: list[float] = []
    for i, fact in enumerate(truth):
        got = pattern_map.get(i + 1, "").lower()
        ans = fact["ans"].lower()
        ok = ans in got or any(tok in got for tok in ans.split() if len(tok) > 3)
        field_scores.append(1.0 if ok else 0.0)
    return {
        "score": round(sum(field_scores) / len(field_scores), 3),
        "hits": int(sum(field_scores)),
        "total": len(field_scores),
        "per_question": pattern_map,
    }


def _count_notes(workdir: Path) -> int:
    notes_dir = workdir / ".memory-graph" / "notes"
    if not notes_dir.exists():
        return 0
    return sum(1 for _ in notes_dir.rglob("*.md"))


async def run_arm(arm: str) -> dict[str, Any]:
    ts = time.strftime("%Y%m%d-%H%M%S")
    workdir = WORK_BASE / f"b11-{arm}-{ts}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    _generate_codebase(workdir)

    if arm == "with_memory":
        subprocess.run(
            [str(PIPX_MEMORY_GRAPH), "init"],
            cwd=str(workdir),
            check=True,
            capture_output=True,
        )

    print(f"=== B11 ARM: {arm} ===")
    print(f"  workdir: {workdir}")
    print("  phase 1 (investigate)    ... ", end="", flush=True)
    p1 = await run_phase(PHASE1_PROMPT, workdir, with_memory=(arm == "with_memory"), max_turns=90)
    notes_after_p1 = _count_notes(workdir)
    print(f"{p1['seconds']}s  cost=${p1['cost_usd'] or 0:.4f}  notes={notes_after_p1}")

    # SOURCE STAYS — this is the key difference from B7.
    questions = "\n".join(f"Q{i + 1:02d}: {f['question']}" for i, f in enumerate(FACTS))

    print("  phase 2 (recall, files PRESENT) ... ", end="", flush=True)
    p2 = await run_phase(
        PHASE2_PROMPT.format(questions=questions),
        workdir,
        with_memory=(arm == "with_memory"),
        max_turns=90,
    )
    print(f"{p2['seconds']}s  cost=${p2['cost_usd'] or 0:.4f}")

    sc = grade(p2["text"], FACTS)
    print(f"  score: {sc['hits']}/{sc['total']}  ({sc['score']:.2%})")

    return {
        "arm": arm,
        "score": sc,
        "phase1": {k: v for k, v in p1.items() if k != "text"},
        "phase2": {k: v for k, v in p2.items() if k != "text"},
        "notes_written_in_phase1": notes_after_p1,
        "total_cost_usd": (p1.get("cost_usd") or 0) + (p2.get("cost_usd") or 0),
        "phase2_cost_usd": p2.get("cost_usd") or 0,
        "phase2_seconds": p2["seconds"],
        "total_seconds": round(p1["seconds"] + p2["seconds"], 1),
    }


async def main_async() -> int:
    print("=" * 64)
    print("B11: Cross-session recall (files STILL PRESENT in phase 2)")
    print("=" * 64)
    no_mem = await run_arm("no_memory")
    with_mem = await run_arm("with_memory")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "b11_xsession_keep.json").write_text(
        json.dumps({"no_memory": no_mem, "with_memory": with_mem}, indent=2)
    )
    print()
    print("FINAL")
    print(f"  no_memory   {no_mem['score']['hits']}/30  "
          f"total=${no_mem['total_cost_usd']:.4f} ({no_mem['total_seconds']}s)  "
          f"phase2=${no_mem['phase2_cost_usd']:.4f} ({no_mem['phase2_seconds']}s)")
    print(f"  with_memory {with_mem['score']['hits']}/30  "
          f"total=${with_mem['total_cost_usd']:.4f} ({with_mem['total_seconds']}s)  "
          f"phase2=${with_mem['phase2_cost_usd']:.4f} ({with_mem['phase2_seconds']}s)  "
          f"notes_p1={with_mem['notes_written_in_phase1']}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
