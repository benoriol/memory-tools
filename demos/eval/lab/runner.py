"""Common harness for iterative benchmark designs.

Each design is a module exposing:
  - NAME, DESCRIPTION
  - LOOPHOLE_CLOSED: what loophole from the previous design this addresses
  - prepare(workdir: Path, seed: int) -> dict[str, Any]   # builds files, returns ground truth
  - PROMPT: str  -- formatted with the ground-truth dict
  - grade(text: str, gt: dict) -> dict[str, Any]   # {parsed, score, breakdown}

Run with:  python runner.py <design_module> [--with-memory]
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Apply system limits before any heavy imports.
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
    os.environ["HIP_VISIBLE_DEVICES"] = ""
    os.environ["ROCR_VISIBLE_DEVICES"] = ""


_apply_limits()

REPO_ROOT = Path(__file__).resolve().parents[3]
PIPX_MEMORY_GRAPH = Path.home() / ".local" / "bin" / "memory-graph"
RESULTS_DIR = REPO_ROOT / "demos" / "eval" / "results" / "lab"
WORK_BASE = Path("/tmp/lab-bench")


def _load_design(name: str):
    path = Path(__file__).parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def run_arm(
    workdir: Path,
    prompt: str,
    *,
    with_memory: bool,
    model: str = "claude-sonnet-4-6",
    effort: str = "low",
    max_turns: int = 80,
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
            "mcp__memory-graph__memory_link",
            "mcp__memory-graph__memory_supersede",
        ]
        mcp_servers["memory-graph"] = {
            "command": str(PIPX_MEMORY_GRAPH),
            "args": ["serve"],
        }

    options = ClaudeAgentOptions(
        model=model,
        effort=effort,
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


async def main_async(args):
    design = _load_design(args.design)
    ts = time.strftime("%Y%m%d-%H%M%S")
    arm = "with_memory" if args.with_memory else "no_memory"
    workdir = WORK_BASE / f"{args.design}-{arm}-{ts}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    print(f"=== design: {args.design} ({arm}) ===")
    print(f"  what:  {design.DESCRIPTION}")
    if hasattr(design, "LOOPHOLE_CLOSED"):
        print(f"  closes: {design.LOOPHOLE_CLOSED}")
    print(f"  workdir: {workdir}")

    gt = design.prepare(workdir, seed=args.seed)
    if args.with_memory:
        subprocess.run(
            [str(PIPX_MEMORY_GRAPH), "init"],
            cwd=str(workdir),
            check=True,
            capture_output=True,
        )

    prompt = design.PROMPT.format(**gt) if "{" in design.PROMPT else design.PROMPT

    print("  running ... ", end="", flush=True)
    res = await run_arm(
        workdir,
        prompt,
        with_memory=args.with_memory,
        max_turns=args.max_turns,
    )
    print(f"{res['seconds']}s  cost=${res['cost_usd'] or 0:.4f}")

    score = design.grade(res["text"], gt)
    print(f"  score: {json.dumps(score, indent=None)}")
    tail = "\n".join(res["text"].splitlines()[-15:])
    print(f"  tail:\n---\n{tail}\n---")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "design": args.design,
        "arm": arm,
        "ground_truth_summary": {k: v for k, v in gt.items() if k != "_full"},
        "score": score,
        "cost_usd": res["cost_usd"],
        "seconds": res["seconds"],
        "usage": res["usage"],
        "text_tail": tail,
        "workdir": str(workdir),
    }
    (RESULTS_DIR / f"{args.design}-{arm}.json").write_text(json.dumps(out, indent=2))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("design", help="design module name, e.g. b2_semantic")
    parser.add_argument("--with-memory", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-turns", type=int, default=80)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
