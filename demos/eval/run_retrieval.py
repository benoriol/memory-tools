"""Run the retrieval benchmark against a synthetic Mango graph.

Invokes `memory_retrieve` (orchestration layer) for each task, captures
the sub-agent's synthesis, and grades it against a deterministic
checklist of "must mention" substrings. Reports per-tier accuracy plus
a summary including total token usage and an estimated cost.

Usage:
    python -m demos.eval.run_retrieval \\
        --store /tmp/eval-retrieval/.memory-graph \\
        --tasks demos/eval/retrieval_tasks.json \\
        --results demos/eval/results/retrieval-<ts>.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

from memory_graph.embed import LocalEmbedder
from memory_graph.orchestration.runner import (
    DEFAULT_EFFORT,
    DEFAULT_MODEL,
    build_sdk_tools,
    compose_system_prompt,
)
from memory_graph.primitives import Store

# Eval-specific override: the user asked for "fast but competent" — use Haiku.
EVAL_MODEL = "claude-haiku-4-5-20251001"
EVAL_EFFORT = "low"

# Rough Haiku 4.5 pricing (per 1M tokens).
PRICE_INPUT_PER_M = 1.00
PRICE_OUTPUT_PER_M = 5.00


async def run_one(
    store: Store,
    *,
    question: str,
    intent: str,
) -> dict[str, Any]:
    """Invoke memory_retrieve via Agent SDK, capturing synthesis + usage."""
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        create_sdk_mcp_server,
        query,
    )

    system_prompt = compose_system_prompt("retrieve", store.root)
    server = create_sdk_mcp_server(name="memory", tools=build_sdk_tools(store))
    options = ClaudeAgentOptions(
        model=EVAL_MODEL,
        effort=EVAL_EFFORT,
        system_prompt=system_prompt,
        mcp_servers={"memory": server},
        allowed_tools=[f"mcp__memory__{name}" for name in (
            "search", "get", "neighbors", "status",
        )],
    )

    chunks: list[str] = []
    in_tokens = out_tokens = 0
    t0 = time.monotonic()
    async for msg in query(prompt=f"intent: {intent}\n\n{question}", options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                t = getattr(block, "text", None)
                if t:
                    chunks.append(t)
        elif isinstance(msg, ResultMessage):
            usage = getattr(msg, "usage", None) or {}
            # The SDK reports both per-turn and cumulative; the final ResultMessage
            # carries the cumulative figure in most builds.
            in_tokens += int(usage.get("input_tokens", 0) or 0)
            out_tokens += int(usage.get("output_tokens", 0) or 0)
    return {
        "synthesis": "\n".join(chunks).strip(),
        "in_tokens": in_tokens,
        "out_tokens": out_tokens,
        "seconds": round(time.monotonic() - t0, 1),
    }


def grade(synthesis: str, must_mention: list[str], bonus_mention: list[str]) -> dict[str, Any]:
    text = (synthesis or "").lower()
    must_hits = [s for s in must_mention if s.lower() in text]
    bonus_hits = [s for s in bonus_mention if s.lower() in text]
    must_score = len(must_hits) / max(1, len(must_mention))
    bonus_score = 0.5 * len(bonus_hits) / max(1, len(bonus_mention)) if bonus_mention else 0.0
    return {
        "must_hits": must_hits,
        "must_missed": [s for s in must_mention if s not in must_hits],
        "bonus_hits": bonus_hits,
        "must_score": round(must_score, 3),
        "bonus_score": round(bonus_score, 3),
        "score": round(min(1.0, must_score + bonus_score), 3),
    }


async def run_all(store_root: Path, tasks_path: Path) -> dict[str, Any]:
    tasks = json.loads(tasks_path.read_text())
    store = Store(store_root, embedder=LocalEmbedder())
    results: dict[str, Any] = {
        "model": EVAL_MODEL,
        "effort": EVAL_EFFORT,
        "tiers": {},
        "tasks": [],
        "totals": {"in_tokens": 0, "out_tokens": 0, "seconds": 0.0},
    }
    try:
        for tier in ("easy", "medium", "hard"):
            tier_results = []
            for task in tasks[tier]:
                print(f"  [{tier:6}] {task['id']} … ", end="", flush=True)
                ret = await run_one(
                    store, question=task["question"], intent=task["intent"]
                )
                g = grade(
                    ret["synthesis"], task["must_mention"], task.get("bonus_mention") or []
                )
                row = {
                    "id": task["id"],
                    "tier": tier,
                    "question": task["question"],
                    "intent": task["intent"],
                    **ret,
                    **g,
                }
                tier_results.append(row)
                results["tasks"].append(row)
                results["totals"]["in_tokens"] += ret["in_tokens"]
                results["totals"]["out_tokens"] += ret["out_tokens"]
                results["totals"]["seconds"] += ret["seconds"]
                print(f"score={g['score']:.2f}  ({ret['seconds']}s, "
                      f"{ret['in_tokens']}+{ret['out_tokens']} tok)")
            tier_results.sort(key=lambda r: r["id"])
            results["tiers"][tier] = {
                "mean_score": round(
                    sum(r["score"] for r in tier_results) / max(1, len(tier_results)), 3
                ),
                "task_count": len(tier_results),
            }
    finally:
        store.close()

    # Cost estimate.
    totals = results["totals"]
    cost = (
        totals["in_tokens"]  / 1_000_000 * PRICE_INPUT_PER_M
        + totals["out_tokens"] / 1_000_000 * PRICE_OUTPUT_PER_M
    )
    results["totals"]["estimated_cost_usd"] = round(cost, 4)
    results["totals"]["seconds"] = round(totals["seconds"], 1)
    return results


def print_summary(results: dict[str, Any]) -> None:
    print("\n" + "=" * 72)
    print("RETRIEVAL BENCHMARK")
    print("=" * 72)
    print(f"model:   {results['model']}  (effort={results['effort']})")
    print()
    print(f"{'tier':<10}{'tasks':<8}{'mean score':<14}")
    print("-" * 32)
    for tier in ("easy", "medium", "hard"):
        t = results["tiers"][tier]
        print(f"{tier:<10}{t['task_count']:<8}{t['mean_score']:<14}")
    overall = sum(t["mean_score"] for t in results["tiers"].values()) / 3
    print(f"{'overall':<10}{'':8}{round(overall,3):<14}")
    print()
    totals = results["totals"]
    print(f"total runtime: {totals['seconds']}s")
    print(f"total tokens:  {totals['in_tokens']} input + {totals['out_tokens']} output")
    print(f"est. cost:     ${totals['estimated_cost_usd']}")
    print()

    # Per-task miss table.
    misses = [r for r in results["tasks"] if r["score"] < 1.0]
    if misses:
        print("Tasks with non-perfect score:")
        for r in misses:
            print(f"  {r['tier']:6}  {r['id']:<28}  score={r['score']:.2f}  "
                  f"missed: {r['must_missed']}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--store", required=True, help="path to .memory-graph/ dir")
    p.add_argument("--tasks", required=True, help="path to retrieval_tasks.json")
    p.add_argument("--results", required=True, help="path to write results JSON")
    args = p.parse_args(argv)

    results = asyncio.run(run_all(Path(args.store), Path(args.tasks)))
    Path(args.results).parent.mkdir(parents=True, exist_ok=True)
    Path(args.results).write_text(json.dumps(results, indent=2))
    print_summary(results)
    print(f"\nfull results: {args.results}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
