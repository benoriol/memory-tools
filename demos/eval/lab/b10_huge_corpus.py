"""B10: Corpus large enough to truly exceed context (~6MB).

3000 docs × ~2KB = ~6MB ≈ 1.5M tokens. Sonnet's context is 1M tokens, so
the corpus cannot all live in context simultaneously. The agent must be
selective.

Queries are paraphrased: the question's wording is not present in the
matching document. grep on question terms returns zero hits.

Strategy choices the agent might make:
  - no_memory: must scan via Bash on the filesystem (grep with broader
    keyword sets), risk missing semantic matches.
  - with_memory: sweep once, capture per-doc summaries, then use
    memory_search (semantic) per question.

Hypothesis: at this size, with_memory either wins on accuracy (no_memory
misses semantic matches) or on cost (no_memory does many wasted reads).
"""

from __future__ import annotations

import asyncio
import json
import os
import random
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
        print(f"[limits] {exc}", file=sys.stderr)
    try:
        cpus = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, set(cpus[:CPU_CORES_CAP]))
    except (AttributeError, OSError) as exc:
        print(f"[limits] {exc}", file=sys.stderr)
    os.environ["CUDA_VISIBLE_DEVICES"] = ""


_apply_limits()


REPO_ROOT = Path(__file__).resolve().parents[3]
PIPX_MEMORY_GRAPH = Path.home() / ".local" / "bin" / "memory-graph"
RESULTS_DIR = REPO_ROOT / "demos" / "eval" / "results" / "lab"
WORK_BASE = Path("/tmp/lab-bench")


N_DOCS = 3000
N_QUESTIONS = 20

NAMES = [
    "Quennel", "Crispel", "Halberd", "Threnody", "Pyrethorn", "Veristone",
    "Folwark", "Sondheim", "Praewyn", "Thurible", "Brindlewell", "Stelluna",
    "Mirepoix", "Pellinor", "Vexford", "Karstmere", "Verisade", "Cinderwood",
    "Argentbridge", "Outhewn", "Sundappur", "Coelibrant", "Cathlock", "Threpwood",
    "Halberdsworth", "Inglemoore", "Mvorra", "Slathe", "Ravenmark", "Plumelay",
    "Larkmount", "Glanwood", "Heliodon", "Argo-Stelloth",
]

DOC_QUESTION_PAIRS = [
    ("transactional consistency across billing tables",
     "ACID guarantees for accounting records"),
    ("tail-latency budget at p95 under spike conditions",
     "long-tail response time during traffic bursts"),
    ("operational overhead unjustifiable for our headcount",
     "running it ourselves would cost too many people"),
    ("forced upgrades of installed mobile clients",
     "we can't push new versions to phones already in the field"),
    ("storage cost at 100% sampling exceeded the budget",
     "keeping every trace would blow the observability cost"),
    ("watch-based change notification semantics",
     "real-time observation of config-key changes"),
    ("precise per-tenant priority weighting",
     "per-customer fairness controls in the job queue"),
    ("CPU throughput economical relative to GPU at our scale",
     "running on graphics cards too expensive for the throughput"),
    ("centralized token-revocation requirement",
     "log a user out across all services at once"),
    ("data should land in the customer's environment",
     "result delivered to the customer's own infrastructure"),
    ("indexable by search engines and first-contentful-paint",
     "search-engine crawling and initial render speed"),
    ("schema drift in ad-hoc JSON payloads",
     "fields silently changing without wire-format enforcement"),
    ("egress bills from hot images fetched from origin",
     "the AWS bandwidth bill for popular media"),
    ("targeting DSL would cost engineer-months to replicate",
     "the rule language for flag evaluation is hard to rebuild"),
    ("replay and retention story",
     "the ability to re-process old messages and keep them around"),
    ("pay-per-query versus committed compute pricing",
     "billing per scan rather than reserved capacity"),
    ("tamper-evident audit log for SOC2",
     "compliance proof records cannot be altered"),
    ("duplicate writes deemed acceptable; aggregations idempotent",
     "dedup skipped because dashboards don't care"),
    ("BYOK to land a specific enterprise contract",
     "customer-controlled encryption keys, added to win a particular deal"),
    ("bursty traffic patterns made percentage-shifting meaningless",
     "spiky load made gradual rollout useless"),
]


def _doc_text(name: str, replaced: str, doc_phrase: str, rng: random.Random) -> str:
    bg = " ".join(
        rng.sample(
            [
                "Operational characteristics dominated the decision matrix.",
                "Engineer-time was the binding constraint throughout.",
                "Customer-visible behavior took precedence over internal elegance.",
                "Operating model and budgetary realities both contributed.",
                "Long-tail customer environments influenced the final pick.",
                "Bench profiling against representative workloads guided the call.",
                "Initial prototypes were built against three alternatives.",
                "Performance was measured under simulated peak load.",
                "Cost forecasts under three-year growth scenarios were modeled.",
                "Two trade-offs were weighed in successive design reviews.",
            ],
            k=3,
        )
    )
    return (
        f"We adopted {name}. The deciding factor was {doc_phrase}. "
        f"We had previously considered {replaced} but moved away from it.\n\n"
        f"## Background\n{bg}\n\n"
        f"## Trade-offs\n"
        f"Selecting {name} over {replaced} came with operational trade-offs. "
        f"Tooling and observability around {name} are mature enough for use.\n\n"
        f"## Risks\n"
        f"Supplier concentration is the principal risk; we mitigate by keeping "
        f"the integration thin enough that a future migration is tractable.\n\n"
        f"## Decision\nWe will use {name}. {replaced} is retired from consideration.\n"
    )


def prepare(workdir: Path, seed: int = 0) -> dict[str, Any]:
    workdir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed + 41)

    # Each doc uses one name (with index suffix to keep unique) and one
    # doc-phrase. Filler phrases dilute non-answer docs.
    filler = [
        "team morale considerations",
        "vendor relationship continuity",
        "alignment with the platform roadmap",
        "operational simplicity over flexibility",
        "third-party support availability",
        "alignment with the FY budget",
        "minimizing migration risk",
        "shorter time-to-production",
        "consistency with the rest of the stack",
        "preference of the on-call team",
        "documentation maturity",
        "community ecosystem health",
        "the principal engineer's preference",
        "compatibility with existing CI/CD",
        "cost predictability under growth",
    ]

    # Answer-doc indices: random N_QUESTIONS distinct indices
    all_idx = list(range(N_DOCS))
    rng.shuffle(all_idx)
    answer_idx = all_idx[:N_QUESTIONS]

    phrases_for: dict[int, str] = {}
    names_for: dict[int, str] = {}
    for q_idx, doc_idx in enumerate(answer_idx):
        phrases_for[doc_idx] = DOC_QUESTION_PAIRS[q_idx][0]
        # Pick a unique name suffix
        names_for[doc_idx] = f"{rng.choice(NAMES)}{doc_idx:04d}"

    for i in range(N_DOCS):
        if i in phrases_for:
            name = names_for[i]
            phrase = phrases_for[i]
        else:
            name = f"{rng.choice(NAMES)}{i:04d}"
            phrase = rng.choice(filler)
        replaced = f"{rng.choice(NAMES)}-Alt"
        (workdir / f"d{i:05d}.md").write_text(_doc_text(name, replaced, phrase, rng))

    questions = []
    for q_idx, doc_idx in enumerate(answer_idx):
        qid = f"Q{q_idx + 1:02d}"
        paraphrase = DOC_QUESTION_PAIRS[q_idx][1]
        questions.append((
            qid,
            f"Which component was chosen because of {paraphrase}?",
            f"d{doc_idx:05d}",
            names_for[doc_idx],
        ))

    (workdir / "_ground_truth.json").write_text(
        json.dumps(
            {"n_docs": N_DOCS, "n_questions": len(questions),
             "answers": {qid: name for qid, _, _, name in questions}},
            indent=2,
        )
    )
    return {"questions": questions, "n_docs": N_DOCS}


PROMPT_BASE = """\
This directory contains {n_docs} markdown files (d00000.md .. d{last:05d}.md).
Each describes one architectural decision. Component names are made up.
Total corpus: {mb:.1f} MB — this exceeds what fits comfortably in one
context window.

You will answer {n_questions} questions. Each is PARAPHRASED — the
question's wording does NOT appear verbatim in the matching document.
Example: question says "ACID guarantees" while the doc says "transactional
consistency".

Output the LAST {n_questions} lines of your response in EXACTLY:

Q01: <name>
Q02: <name>
...
Q{n_questions:02d}: <name>
"""

NO_MEM_TAIL = """\

You have Read, Bash, Glob, Grep, Write, Edit. Choose any approach.

Questions:
{questions}
"""

MEM_TAIL = """\

You have memory tools (mcp__memory-graph__memory_capture_batch,
memory_search, memory_retrieve, memory_status) plus Read/Bash/Grep/Write.

REQUIRED: actually use memory tools. Specifically:
  1. Sweep the corpus once. For each batch of ~25 docs, read them and call
     memory_capture_batch with one note per doc whose summary contains
     the component name AND a paraphrased description of the deciding factor.
  2. After all docs are captured, for each question call memory_search with
     the question's concept. The semantic embedding will surface the
     matching note even though the question's words differ from the doc.
  3. Answer.

If you don't use memory tools this benchmark is meaningless, so please
actually use them.

Questions:
{questions}
"""


async def run_arm(arm: str) -> dict[str, Any]:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        query,
    )

    ts = time.strftime("%Y%m%d-%H%M%S")
    workdir = WORK_BASE / f"b10-{arm}-{ts}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    print(f"=== B10 ARM: {arm} ===")
    print("  generating corpus ...", end=" ", flush=True)
    t_gen = time.monotonic()
    gt = prepare(workdir)
    print(f"{time.monotonic() - t_gen:.1f}s")

    total_bytes = sum(p.stat().st_size for p in workdir.glob("d*.md"))
    print(f"  workdir: {workdir}  corpus: {total_bytes/1024/1024:.2f} MB across {gt['n_docs']} docs")

    if arm == "with_memory":
        subprocess.run(
            [str(PIPX_MEMORY_GRAPH), "init"],
            cwd=str(workdir), check=True, capture_output=True,
        )

    allowed = ["Read", "Bash", "Glob", "Grep", "Write", "Edit"]
    mcp_servers: dict[str, Any] = {}
    if arm == "with_memory":
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

    questions_text = "\n".join(f"{qid}: {q}" for qid, q, _, _ in gt["questions"])
    tail = MEM_TAIL if arm == "with_memory" else NO_MEM_TAIL
    prompt = PROMPT_BASE.format(
        n_docs=gt["n_docs"], last=gt["n_docs"] - 1,
        mb=total_bytes / 1024 / 1024,
        n_questions=len(gt["questions"]),
    ) + tail.format(questions=questions_text)

    options = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        effort="low",
        permission_mode="bypassPermissions",
        cwd=str(workdir),
        allowed_tools=allowed,
        mcp_servers=mcp_servers,
        max_turns=200,
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
    text = "\n".join(text_chunks).strip()
    usage = dict(getattr(last_result, "usage", None) or {}) if last_result else {}
    cost = getattr(last_result, "total_cost_usd", None) if last_result else None
    seconds = round(time.monotonic() - t0, 1)

    import re
    hits = 0
    per_q: dict[str, str] = {}
    for qid, _q, _did, key in gt["questions"]:
        m = re.search(rf"{qid}\s*:\s*(.+)", text)
        ans = m.group(1).strip() if m else ""
        per_q[qid] = ans
        if key.lower() in ans.lower():
            hits += 1

    notes_dir = workdir / ".memory-graph" / "notes"
    n_notes = sum(1 for _ in notes_dir.glob("*.md")) if notes_dir.is_dir() else 0
    scratch_files = [
        p.name for p in workdir.iterdir()
        if p.is_file() and p.name.endswith((".json", ".txt", ".csv"))
        and not p.name.startswith("d") and p.name != "_ground_truth.json"
    ]

    print(f"  time: {seconds}s  cost: ${cost or 0:.4f}  score: {hits}/{len(gt['questions'])}")
    print(f"  usage: in={usage.get('input_tokens',0)} out={usage.get('output_tokens',0)} "
          f"cache_read={usage.get('cache_read_input_tokens',0)} "
          f"cache_create={usage.get('cache_creation_input_tokens',0)}")
    print(f"  memory_notes_written: {n_notes}  scratch_files: {scratch_files[:5]}")
    return {
        "arm": arm,
        "score": hits,
        "total": len(gt["questions"]),
        "cost_usd": cost,
        "seconds": seconds,
        "usage": usage,
        "per_question": per_q,
        "memory_notes": n_notes,
        "scratch_files": scratch_files,
        "corpus_mb": round(total_bytes / 1024 / 1024, 2),
        "workdir": str(workdir),
    }


async def main_async() -> int:
    print("=" * 64)
    print(f"B10: {N_DOCS} docs (~6MB), {N_QUESTIONS} paraphrased queries")
    print("=" * 64)
    no_mem = await run_arm("no_memory")
    with_mem = await run_arm("with_memory")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "b10_huge_corpus.json").write_text(
        json.dumps({"no_memory": no_mem, "with_memory": with_mem}, indent=2)
    )
    print()
    print("FINAL")
    print(f"  no_memory   score={no_mem['score']}/{no_mem['total']}  cost=${no_mem['cost_usd'] or 0:.4f}  time={no_mem['seconds']}s  notes={no_mem['memory_notes']}")
    print(f"  with_memory score={with_mem['score']}/{with_mem['total']}  cost=${with_mem['cost_usd'] or 0:.4f}  time={with_mem['seconds']}s  notes={with_mem['memory_notes']}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
