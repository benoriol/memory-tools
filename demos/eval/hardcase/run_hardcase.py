"""Hardcase benchmark: one task that requires memory to solve.

Phase 1: agent runs scenario.py, reads witness statements, deduces the
         five facts. With memory: captures them. Without: just observes.
Phase 1.5 (system): scenario.py is DELETED. No artifact on disk
         contains the witnesses or the answer.
Phase 2: agent submits a report with the five facts.

Order is strict: no_memory runs first. If it scores ≥ 0.5, the
benchmark isn't isolating memory's value and we abort rather than
claim victory on the with_memory arm.

Grading: phase 2's final assistant text is parsed for five fact
categories. Each correct = 1/5. Evidence category counts each of three
pieces as 1/3 of that field.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = REPO_ROOT / "demos" / "eval" / "hardcase" / "scenario.py"
PIPX_MEMORY_GRAPH = Path.home() / ".local" / "bin" / "memory-graph"
RESULTS_DIR = REPO_ROOT / "demos" / "eval" / "results"

# Acceptable substrings (case-insensitive) for each fact field.
GROUND_TRUTH: dict[str, list[Any]] = {
    "culprit": ["eleanor vance", "eleanor"],
    "motive": ["inheritance", "inherit", "the will"],
    "weapon": ["letter opener", "stiletto"],
    "location": ["library"],
    # Three evidence categories; each = list of synonyms; field credit is
    # number_of_categories_hit / 3.
    "evidence": [
        ["muddy footprint", "footprint", "narrow shoe", "woman's shoe", "narrow prints"],
        ["argument", "heated voices", "won't be left with nothing", "shouting", "raised voices"],
        ["inheritance", "will", "whitfield", "solicitor", "financial motive"],
    ],
}

PHASE_1_PROMPT = """\
You are investigating an incident at Whitfield Manor.

STEP 1: Run `python scenario.py` to read the six witness statements.
        (You can run it with the Bash tool.)

STEP 2: Cross-reference the statements to deduce these FIVE facts:
   - WHO is responsible (full name)
   - Their MOTIVE
   - The WEAPON used
   - The LOCATION where it happened
   - THREE specific pieces of evidence supporting your conclusion

STEP 3: Document your findings THOROUGHLY.

CRITICAL: scenario.py will be DELETED after this phase. The witness
statements only exist in stdout when you run the script — they are not
saved to any file. This is your ONLY opportunity to preserve the
findings.

If you have memory tools (memory_* / mcp__memory-graph__*), USE THEM
to capture each deduced fact and the supporting evidence. This is the
only mechanism that survives into the next session.

If you do NOT have memory tools available, simply print your findings
clearly — though they will not be available in the next phase, only
this single session can use them.
"""

PHASE_2_PROMPT = """\
Submit your FINAL REPORT on the Whitfield Manor incident.

A prior investigation phase has already gathered the case findings. Your
task in this phase is to retrieve those findings and present them.

REQUIRED FIRST ACTIONS (do these BEFORE attempting to answer):

  1. If you have a tool whose name starts with `mcp__memory-graph__`
     (memory_retrieve, memory_search, memory_status, memory_get,
     memory_neighbors), CALL THEM NOW. Specifically:
        - call `memory_status` to see if a graph exists
        - call `memory_retrieve` with a query like "Whitfield Manor
          incident culprit weapon location motive evidence"
        - if the retrieve synthesis is thin, also call `memory_search`
          on individual terms ("culprit", "weapon", "evidence")
        - read full notes via `memory_get` if you need detail
     ONLY AFTER exhausting these tools should you consider the case
     undocumented.

  2. If after using the memory tools you genuinely have no information,
     state that. But the prior investigation DID capture findings — they
     are in the memory graph. Do not give up before checking.

Once you have the case information, output your report in EXACTLY this
format. Do NOT add caveats like "based on memory" or "if I understand
correctly" — commit to your best answer for each field:

CULPRIT: <full name>
MOTIVE: <one short phrase>
WEAPON: <specific object>
LOCATION: <specific room>
EVIDENCE: <three distinct pieces, separated by semicolons>
"""


async def run_phase(prompt: str, workdir: Path, *, with_memory: bool) -> dict[str, Any]:
    """Run one phase via Agent SDK. Returns text + usage + cost + timing."""
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        query,
    )

    allowed = ["Read", "Edit", "Write", "Bash", "Glob", "Grep"]
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
            "mcp__memory-graph__memory_link",
            "mcp__memory-graph__memory_supersede",
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
        max_turns=30,
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


def grade(report: str) -> tuple[float, dict[str, float]]:
    text = (report or "").lower()
    field_scores: dict[str, float] = {}
    for field, accept in GROUND_TRUTH.items():
        if field == "evidence":
            hits = sum(
                1
                for synonyms in accept
                if any(s.lower() in text for s in synonyms)
            )
            field_scores[field] = hits / 3
        else:
            field_scores[field] = (
                1.0 if any(s.lower() in text for s in accept) else 0.0
            )
    overall = sum(field_scores.values()) / len(field_scores)
    return overall, field_scores


async def run_arm(arm: str) -> dict[str, Any]:
    print(f"\n=== ARM: {arm} ===")
    ts = time.strftime("%Y%m%d-%H%M%S")
    workdir = Path(f"/tmp/hardcase-{arm}-{ts}")
    workdir.mkdir(parents=True)
    shutil.copy(TEMPLATE, workdir / "scenario.py")

    if arm == "with_memory":
        subprocess.run(
            [str(PIPX_MEMORY_GRAPH), "init"],
            cwd=str(workdir), check=True, capture_output=True,
        )

    print(f"  workdir: {workdir}")
    print("  phase 1 (investigate) ... ", end="", flush=True)
    p1 = await run_phase(PHASE_1_PROMPT, workdir, with_memory=(arm == "with_memory"))
    print(f"{p1['seconds']}s")

    # PURGE: remove scenario.py so phase 2 cannot re-read it.
    (workdir / "scenario.py").unlink(missing_ok=True)
    # Also remove anything the agent might have written that contains the answer.
    # (We're paranoid — see if the agent created any notes file in cwd.)
    for path in workdir.rglob("*"):
        if path.is_file() and path.name not in (".mcp.json",):
            # Skip the memory store internals (with_memory arm needs them).
            if ".memory-graph" in path.parts:
                continue
            # Skip nothing else — anything in cwd that the agent wrote during
            # phase 1 would be cheating. We delete it.
            try:
                path.unlink()
            except OSError:
                pass
    print("  scenario.py and any phase-1 outputs PURGED from cwd")

    print("  phase 2 (report)      ... ", end="", flush=True)
    p2 = await run_phase(PHASE_2_PROMPT, workdir, with_memory=(arm == "with_memory"))
    print(f"{p2['seconds']}s")

    score, field_scores = grade(p2["text"])
    print(f"  score: {score:.2f}   fields: " + ", ".join(
        f"{k}={v:.2f}" for k, v in field_scores.items()
    ))
    print(f"  report:\n---\n{p2['text'][:1500]}\n---")

    in_toks = (p1["usage"].get("input_tokens", 0) + p2["usage"].get("input_tokens", 0))
    out_toks = (p1["usage"].get("output_tokens", 0) + p2["usage"].get("output_tokens", 0))
    return {
        "arm": arm,
        "score": round(score, 3),
        "field_scores": field_scores,
        "phase1": p1,
        "phase2": p2,
        "total_in_tokens": in_toks,
        "total_out_tokens": out_toks,
        "total_seconds": round(p1["seconds"] + p2["seconds"], 1),
        "total_cost_usd": (p1.get("cost_usd") or 0) + (p2.get("cost_usd") or 0),
    }


async def main() -> int:
    print("=" * 64)
    print("THE WHITFIELD MANOR HARDCASE")
    print("One task. Memory required.")
    print("=" * 64)

    # PASS 1: no_memory. This MUST fail (≥ 50% would mean the benchmark
    # didn't isolate memory's value).
    no_mem = await run_arm("no_memory")

    if no_mem["score"] >= 0.5:
        print()
        print("=" * 64)
        print("ABORTING: no_memory scored >= 0.50.")
        print("The benchmark did not successfully isolate memory's value.")
        print("Not running with_memory arm — refusing to claim a fake win.")
        print("=" * 64)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / "hardcase-aborted.json").write_text(
            json.dumps({"no_memory": no_mem, "aborted": True}, indent=2)
        )
        return 2

    print()
    print(f"OK: no_memory scored {no_mem['score']:.2f} (< 0.50). Proceeding to with_memory arm.")

    # PASS 2: with_memory.
    with_mem = await run_arm("with_memory")

    print()
    print("=" * 64)
    print("FINAL RESULTS")
    print("=" * 64)
    print(f"  no_memory   score: {no_mem['score']:.2f}   cost: ${no_mem['total_cost_usd']:.4f}   time: {no_mem['total_seconds']}s")
    print(f"  with_memory score: {with_mem['score']:.2f}   cost: ${with_mem['total_cost_usd']:.4f}   time: {with_mem['total_seconds']}s")
    print(f"  delta:              {with_mem['score'] - no_mem['score']:+.2f}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "hardcase-result.json").write_text(
        json.dumps({"no_memory": no_mem, "with_memory": with_mem}, indent=2)
    )
    print(f"\nfull results: {RESULTS_DIR / 'hardcase-result.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
