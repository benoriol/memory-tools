"""Holistic benchmark: investigate → fix → verify, with and without memory.

For each trial:
  - Fresh copy of the ministats CLI template at /tmp/holistic-<arm>-<ts>-<n>/
  - Three phases run via claude_agent_sdk.query():
      Phase 1: investigate the CLI, identify contract violations
      Phase 2: apply the fixes
      Phase 3: verify
  - After phase 3, run pytest objectively and record passing count.
  - Tracks token usage per phase (main agent only — sub-agent tokens
    used by memory_remember/retrieve are *additional* and not visible
    from the main agent's ResultMessage).

The with-memory arm gets the memory-graph MCP server wired in via the
SDK's mcp_servers option; the no-memory arm doesn't have those tools
at all. Both arms share identical phase prompts.

Usage:
  python -m demos.eval.run_holistic --trials 2 \\
        --results demos/eval/results/holistic-<ts>.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

EVAL_MODEL = "claude-haiku-4-5-20251001"
EVAL_EFFORT = "low"

# Approx Haiku 4.5 pricing.
PRICE_INPUT_PER_M = 1.00
PRICE_OUTPUT_PER_M = 5.00

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "demos" / "eval" / "holistic" / "cli_template"
VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"
PIPX_MEMORY_GRAPH = Path.home() / ".local" / "bin" / "memory-graph"


# ---------------------------------------------------------------------------
# Phase prompts — identical across arms.
# ---------------------------------------------------------------------------

PHASE_1 = (
    "Investigate the ministats CLI in this directory.\n"
    "\n"
    "1. Read README.md carefully — it declares THREE behavior contracts.\n"
    "2. Read the existing test file tests/test_cli.py to confirm the contracts.\n"
    "3. Run the CLI yourself on data/sample.csv with both --format=json and "
    "   --format=text and observe the actual output.\n"
    "4. Identify each CONTRACT VIOLATION. For each one, document:\n"
    "     - which file contains the bug\n"
    "     - what the current (buggy) behavior is\n"
    "     - what the precise fix is (function/variable/line if possible)\n"
    "\n"
    "DO NOT apply any fixes yet. This phase is investigation only.\n"
    "\n"
    "If you have a memory system available (memory_* tools), record each "
    "finding in a separate memory note for later use. Otherwise just print "
    "your findings.\n"
)

PHASE_2 = (
    "Apply the fixes that were identified during the prior investigation, "
    "then run the test suite.\n"
    "\n"
    "If you have a memory system, retrieve the prior investigation findings "
    "first (memory_retrieve with a query about the ministats CLI), then "
    "apply each fix. Otherwise: investigate from scratch using the README "
    "as your guide.\n"
    "\n"
    "After applying fixes, run:\n"
    "    .venv/bin/pytest tests/ -q\n"
    "or just `pytest tests/ -q` and report the results.\n"
)

PHASE_3 = (
    "Run the full test suite (`pytest tests/ -q`) and report:\n"
    "  - how many tests passed / failed\n"
    "  - the title of each still-failing test (if any)\n"
    "  - your best guess at what's still wrong\n"
    "\n"
    "If you have a memory system, capture a brief lesson summarizing what "
    "fixed each bug for future reference.\n"
)


async def run_phase(
    prompt: str,
    workdir: Path,
    *,
    with_memory: bool,
) -> dict[str, Any]:
    """Run one phase via the Agent SDK. Returns text + token + timing dict."""
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        query,
    )

    allowed = ["Read", "Edit", "Write", "Bash", "Glob", "Grep"]
    mcp_servers: dict[str, Any] = {}
    if with_memory:
        allowed += ["mcp__memory-graph__memory_remember",
                    "mcp__memory-graph__memory_retrieve",
                    "mcp__memory-graph__memory_compact",
                    "mcp__memory-graph__memory_search",
                    "mcp__memory-graph__memory_get",
                    "mcp__memory-graph__memory_neighbors",
                    "mcp__memory-graph__memory_status",
                    "mcp__memory-graph__memory_capture",
                    "mcp__memory-graph__memory_capture_batch",
                    "mcp__memory-graph__memory_link",
                    "mcp__memory-graph__memory_supersede"]
        mcp_servers["memory-graph"] = {
            "command": str(PIPX_MEMORY_GRAPH),
            "args": ["serve"],
        }

    options = ClaudeAgentOptions(
        model=EVAL_MODEL,
        effort=EVAL_EFFORT,
        permission_mode="bypassPermissions",
        cwd=str(workdir),
        allowed_tools=allowed,
        mcp_servers=mcp_servers,
        max_turns=50,  # safety cap
    )

    text_chunks: list[str] = []
    in_tokens = out_tokens = 0
    t0 = time.monotonic()
    last_usage_seen: dict[str, int] | None = None
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                t = getattr(block, "text", None)
                if t:
                    text_chunks.append(t)
        elif isinstance(msg, ResultMessage):
            usage = getattr(msg, "usage", None) or {}
            if usage:
                last_usage_seen = usage
    if last_usage_seen:
        in_tokens = int(last_usage_seen.get("input_tokens", 0) or 0)
        out_tokens = int(last_usage_seen.get("output_tokens", 0) or 0)
    return {
        "synthesis": "\n".join(text_chunks).strip(),
        "in_tokens": in_tokens,
        "out_tokens": out_tokens,
        "seconds": round(time.monotonic() - t0, 1),
    }


def setup_workdir(arm: str, trial: int) -> Path:
    """Fresh copy of the template under /tmp."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    workdir = Path(f"/tmp/holistic-{arm}-{ts}-{trial}")
    if workdir.exists():
        shutil.rmtree(workdir)
    shutil.copytree(TEMPLATE_DIR, workdir)
    return workdir


def run_pytest(workdir: Path) -> tuple[int, int]:
    """Returns (passed, failed)."""
    r = subprocess.run(
        [str(VENV_PY), "-m", "pytest", "tests/", "-q"],
        cwd=str(workdir),
        capture_output=True,
        text=True,
    )
    out = r.stdout + r.stderr
    # Parse the last summary line, e.g. "3 passed in 0.13s" or "1 failed, 2 passed in 0.13s".
    passed = failed = 0
    for line in reversed(out.splitlines()):
        s = line.strip()
        if "passed" in s or "failed" in s:
            for word, idx in [("passed", -1), ("failed", -1)]:
                pass
            # Parse roughly.
            import re
            m_p = re.search(r"(\d+)\s+passed", s)
            m_f = re.search(r"(\d+)\s+failed", s)
            if m_p:
                passed = int(m_p.group(1))
            if m_f:
                failed = int(m_f.group(1))
            if passed or failed:
                break
    return passed, failed


async def run_trial(arm: str, trial: int) -> dict[str, Any]:
    print(f"\n--- arm={arm} trial={trial} ---")
    workdir = setup_workdir(arm, trial)
    with_memory = arm == "with_memory"
    if with_memory:
        # Init the per-project memory store. We DON'T register via .mcp.json
        # since the SDK's mcp_servers param wires the server in directly.
        subprocess.run(
            [str(PIPX_MEMORY_GRAPH), "init"],
            cwd=str(workdir),
            check=True,
            capture_output=True,
        )

    phases: list[dict[str, Any]] = []
    for i, prompt in enumerate([PHASE_1, PHASE_2, PHASE_3], start=1):
        print(f"  phase {i} … ", end="", flush=True)
        try:
            ret = await run_phase(prompt, workdir, with_memory=with_memory)
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")
            ret = {"synthesis": f"<error: {exc}>", "in_tokens": 0,
                   "out_tokens": 0, "seconds": 0.0, "error": str(exc)}
        ret["phase"] = i
        phases.append(ret)
        print(f"{ret['seconds']}s ({ret['in_tokens']}+{ret['out_tokens']} tok)")

    passed, failed = run_pytest(workdir)
    print(f"  pytest:  {passed} passed / {failed} failed (of 3)")

    return {
        "arm": arm,
        "trial": trial,
        "workdir": str(workdir),
        "phases": phases,
        "pytest_passed": passed,
        "pytest_failed": failed,
        "total_in_tokens": sum(p["in_tokens"] for p in phases),
        "total_out_tokens": sum(p["out_tokens"] for p in phases),
        "total_seconds": round(sum(p["seconds"] for p in phases), 1),
    }


async def run_all(n_trials: int) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for trial in range(1, n_trials + 1):
        for arm in ("with_memory", "no_memory"):
            r = await run_trial(arm, trial)
            results.append(r)
    return aggregate(results)


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "model": EVAL_MODEL,
        "effort": EVAL_EFFORT,
        "trials": results,
        "arms": {},
    }
    for arm in ("with_memory", "no_memory"):
        rows = [r for r in results if r["arm"] == arm]
        if not rows:
            continue
        total_in = sum(r["total_in_tokens"] for r in rows)
        total_out = sum(r["total_out_tokens"] for r in rows)
        cost = (total_in / 1e6 * PRICE_INPUT_PER_M
                + total_out / 1e6 * PRICE_OUTPUT_PER_M)
        summary["arms"][arm] = {
            "n_trials": len(rows),
            "mean_tests_passed": round(
                sum(r["pytest_passed"] for r in rows) / len(rows), 3
            ),
            "total_in_tokens": total_in,
            "total_out_tokens": total_out,
            "estimated_cost_usd": round(cost, 4),
            "mean_seconds_per_trial": round(
                sum(r["total_seconds"] for r in rows) / len(rows), 1
            ),
        }
    return summary


def print_summary(summary: dict[str, Any]) -> None:
    print("\n" + "=" * 72)
    print("HOLISTIC BENCHMARK")
    print("=" * 72)
    print(f"model: {summary['model']} (effort={summary['effort']})")
    print()
    print(f"{'arm':<14}{'trials':<8}{'avg tests':<11}{'tokens':<22}"
          f"{'cost':<10}{'sec/trial':<10}")
    print("-" * 72)
    for arm in ("with_memory", "no_memory"):
        a = summary["arms"].get(arm)
        if not a:
            continue
        toks = f"{a['total_in_tokens']:,} + {a['total_out_tokens']:,}"
        print(f"{arm:<14}{a['n_trials']:<8}"
              f"{a['mean_tests_passed']:<11.2f}"
              f"{toks:<22}"
              f"${a['estimated_cost_usd']:<9.4f}"
              f"{a['mean_seconds_per_trial']:<10.1f}")
    print()

    # Cost-adjusted comparison.
    w = summary["arms"].get("with_memory")
    n = summary["arms"].get("no_memory")
    if w and n:
        print("Comparison:")
        print(f"  tests passed delta: {w['mean_tests_passed'] - n['mean_tests_passed']:+.2f}")
        print(f"  cost ratio (w/n):   {w['estimated_cost_usd'] / max(n['estimated_cost_usd'], 1e-6):.2f}x")
        print(f"  time ratio (w/n):   {w['mean_seconds_per_trial'] / max(n['mean_seconds_per_trial'], 1e-6):.2f}x")
        print()
        print("Note: with_memory token counts here are MAIN-AGENT only. "
              "Sub-agent calls invoked from memory_remember/retrieve consume "
              "additional tokens not visible in this measurement.")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--trials", type=int, default=2)
    p.add_argument("--results", required=True, help="path to write results JSON")
    args = p.parse_args(argv)

    summary = asyncio.run(run_all(args.trials))
    Path(args.results).parent.mkdir(parents=True, exist_ok=True)
    Path(args.results).write_text(json.dumps(summary, indent=2))
    print_summary(summary)
    print(f"\nfull results: {args.results}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
