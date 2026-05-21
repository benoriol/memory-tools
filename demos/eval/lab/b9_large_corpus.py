"""B9 v2: Large corpus + paraphrased queries; memory used explicitly.

Setup unchanged: ~800 docs, ~1.1MB corpus. But:

  - The prompt explicitly INSTRUCTS the with_memory arm to capture findings
    and the no_memory arm to use whatever scratch it prefers.
  - The 20 questions are PARAPHRASED — the driver phrase in the question
    does NOT appear verbatim in the matching document. Grep on the question
    text alone returns no useful hits.

Why this is fair: in real use, users tell the agent how to use the tool.
The question is whether, when the agent uses memory deliberately, the
session is cheaper than the same workload with a scratch file.

We also VERIFY that the memory store actually has notes at the end.
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


N_DOCS = 800
N_QUESTIONS = 20

NAMES = [
    "Quennel", "Crispel", "Halberd", "Threnody", "Pyrethorn", "Veristone",
    "Folwark", "Sondheim", "Praewyn", "Thurible", "Brindlewell", "Stelluna",
    "Mirepoix", "Pellinor", "Vexford", "Karstmere", "Verisade", "Cinderwood",
    "Argentbridge", "Outhewn", "Sundappur", "Coelibrant", "Cathlock", "Threpwood",
    "Halberdsworth", "Inglemoore", "Mvorra", "Slathe", "Ravenmark", "Plumelay",
    "Larkmount", "Glanwood", "Heliodon", "Argo-Stelloth", "Petraval", "Sundford",
    "Mereton", "Wolde", "Kelderbrook", "Helmsdale", "Calderwick", "Brixenholm",
    "Ostmark", "Vimergard", "Whitlock", "Marigold", "Snipefell", "Wickwool",
    "Threllborn", "Yssingar", "Tofteberg", "Pilgrim", "Argentwood", "Stenbrook",
    "Quinault", "Velabrand", "Norquist", "Plover", "Quintain", "Saxbury",
    "Tarrant", "Underholme", "Vendel", "Yarrow", "Zentmeyer", "Aldecoa",
    "Boronson", "Cathcart", "Drachmann", "Eckhart", "Farelle", "Galbraith",
    "Holvik", "Inglehart", "Jorvik", "Kelmscott", "Lyngstrand", "Morwen",
    "Ostby", "Quincy", "Ravens", "Thornleigh",
]

# (doc-phrase, question-paraphrase). The doc uses the doc-phrase; the
# question uses the paraphrase. Different words for the same concept so
# grep on question terms returns nothing useful.
DOC_QUESTION_PAIRS = [
    ("transactional consistency across billing tables",
     "ACID guarantees for accounting workloads"),
    ("tail-latency budget at p95",
     "long-tail response-time targets"),
    ("operational overhead unjustifiable for our headcount",
     "running it ourselves would cost too many people"),
    ("forced upgrades of installed mobile clients",
     "we can't push new versions to phones already in the field"),
    ("storage cost at full sampling rate",
     "keeping every trace would blow the observability budget"),
    ("watch-based change notification semantics",
     "the ability to observe config-key changes in real time"),
    ("precise per-tenant priority weighting",
     "per-customer fairness controls in the job queue"),
    ("CPU throughput cheaper than GPU for our workload",
     "running on graphics cards costs too much for the throughput we need"),
    ("centralized token-revocation requirement",
     "the ability to log out a user across all services"),
    ("data should land in the customer's environment",
     "the customer wants the result in their own infrastructure"),
    ("indexable by search engines and first-contentful-paint",
     "search-engine crawling and initial render speed"),
    ("schema drift in JSON contracts that lacked enforcement",
     "fields silently changing because nobody was checking the wire format"),
    ("egress bills from hot images fetched from origin",
     "the AWS bandwidth bill for popular media"),
    ("targeting DSL would cost engineer-months to replicate",
     "the rule language for flag evaluation is hard to rebuild"),
    ("replay and retention story",
     "the ability to re-process old messages and to keep them around"),
    ("pay-per-query versus committed compute pricing",
     "billing per scan rather than reserved capacity"),
    ("tamper-evident audit log for SOC2",
     "compliance team needs proof records cannot be altered"),
    ("duplicate writes deemed acceptable; aggregations idempotent downstream",
     "we let dedup slip because the dashboards don't care"),
    ("BYOK to land a specific enterprise contract",
     "customer-controlled encryption keys, added to win a particular deal"),
    ("bursty traffic patterns made percentage-shifting meaningless",
     "spiky load made gradual rollout strategies useless"),
]


def _doc_text(i: int, name: str, replaced: str, doc_phrase: str, rng: random.Random) -> str:
    bg = " ".join(
        rng.sample(
            [
                "The team's prior experience shaped many of these calls.",
                "Operational characteristics dominated the decision matrix.",
                "Engineer-time was the binding constraint throughout.",
                "Customer-visible behavior was prioritized over internal elegance.",
                "Two principal trade-offs were weighed in successive design reviews.",
                "Operating model and budgetary realities both contributed.",
                "Long-tail customer environments influenced the final pick.",
                "Bench profiling against representative workloads guided the call.",
                "Initial prototypes were built against three alternatives.",
                "Performance characteristics were measured under simulated peak load.",
                "Cost forecasts under three-year growth scenarios were modeled.",
            ],
            k=4,
        )
    )
    return (
        f"# Decision {i:04d}\n\n"
        f"We adopted {name} after extensive evaluation. The deciding factor "
        f"was {doc_phrase}. We had previously considered {replaced} but moved "
        f"away from it.\n\n"
        f"## Background\n\n{bg}\n\n"
        f"## Trade-offs\n\n"
        f"Selecting {name} over {replaced} came with operational trade-offs. "
        f"Runbooks were updated; the team invested several engineer-weeks. "
        f"Tooling and observability around {name} are mature enough for use.\n\n"
        f"## Risks\n\n"
        f"Supplier and ecosystem concentration is the principal risk. We mitigate "
        f"by keeping the integration thin enough that a future migration is tractable.\n\n"
        f"## Decision\n\nWe will use {name}. {replaced} is retired from "
        f"consideration. Re-evaluation in twelve months.\n"
    )


def prepare(workdir: Path, seed: int = 0) -> dict[str, Any]:
    workdir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed + 23)

    # Build N_DOCS docs. The first len(DOC_QUESTION_PAIRS) docs each use one
    # of the question-keyable doc-phrases. Remaining docs are filler with
    # other doc-phrases that won't match any question.
    chosen_names = rng.sample(NAMES, k=min(N_DOCS, len(NAMES)))
    while len(chosen_names) < N_DOCS:
        extra = rng.choice(NAMES) + str(rng.randint(10, 99))
        if extra not in chosen_names:
            chosen_names.append(extra)

    filler_phrases = [
        "team morale considerations",
        "vendor relationship continuity",
        "alignment with the platform roadmap",
        "operational simplicity",
        "third-party support availability",
        "alignment with the FY budget",
        "minimizing migration risk",
        "shorter time-to-production",
        "consistency with the rest of the stack",
        "preference of the on-call team",
    ]

    answer_docs = []  # (qid, doc_index, name)
    for q_idx, (doc_phrase, _question) in enumerate(DOC_QUESTION_PAIRS):
        # Place this doc at a random index
        doc_idx = rng.randint(0, N_DOCS - 1)
        # Avoid collisions
        while any(a[1] == doc_idx for a in answer_docs):
            doc_idx = rng.randint(0, N_DOCS - 1)
        answer_docs.append((q_idx, doc_idx, chosen_names[doc_idx], doc_phrase))

    # Build doc-phrase per index
    doc_phrase_by_idx: dict[int, str] = {}
    for _q_idx, doc_idx, _name, phrase in answer_docs:
        doc_phrase_by_idx[doc_idx] = phrase
    for i in range(N_DOCS):
        if i not in doc_phrase_by_idx:
            doc_phrase_by_idx[i] = rng.choice(filler_phrases)

    for i in range(N_DOCS):
        name = chosen_names[i]
        replaced = rng.choice([n for n in NAMES if n != name])
        text = _doc_text(i, name, replaced, doc_phrase_by_idx[i], rng)
        (workdir / f"d{i:04d}.md").write_text(text)

    questions = []
    for q_idx, doc_idx, name, _phrase in answer_docs:
        qid = f"Q{q_idx + 1:02d}"
        paraphrase = DOC_QUESTION_PAIRS[q_idx][1]
        q = f"Which component was chosen because of {paraphrase}?"
        questions.append((qid, q, f"d{doc_idx:04d}", name))

    (workdir / "_ground_truth.json").write_text(
        json.dumps(
            {"n_docs": N_DOCS, "n_questions": len(questions),
             "answers": {qid: name for qid, _, _, name in questions}},
            indent=2,
        )
    )
    return {"questions": questions, "n_docs": N_DOCS}


PROMPT_TMPL_NO_MEM = """\
This directory contains {n_docs} markdown files (d0000.md .. d{last:04d}.md),
each describing one architectural decision for a fictional project. All
component names are made up. Total corpus: ~{mb:.1f} MB.

You will answer {n_questions} questions. Each question describes a decision
in PARAPHRASED form — the wording in the question does NOT appear in the
matching document, but the CONCEPT does.

You have Read, Bash, Glob, Grep, Write, Edit. Use any approach you like.
A reasonable strategy is to make one pass over the corpus and build a
scratch index (a file) that you can consult per-question. Do whatever is
most efficient.

Output the LAST {n_questions} lines of your response in EXACTLY:

Q01: <name>
Q02: <name>
...
Q{n_questions:02d}: <name>

Questions:
{questions}
"""

PROMPT_TMPL_MEM = """\
This directory contains {n_docs} markdown files (d0000.md .. d{last:04d}.md),
each describing one architectural decision for a fictional project. All
component names are made up. Total corpus: ~{mb:.1f} MB.

You will answer {n_questions} questions. Each question describes a decision
in PARAPHRASED form — the wording in the question does NOT appear in the
matching document, but the CONCEPT does.

You have memory tools (mcp__memory-graph__memory_capture_batch,
memory_search, memory_retrieve, etc.) plus Read/Bash/Grep.

REQUIRED STRATEGY:
  1. Sweep the corpus once. For each document, capture a memory note whose
     summary mentions the chosen component name AND the deciding factor in
     YOUR OWN paraphrased words. Use memory_capture_batch in chunks of ~20
     for efficiency.
  2. For each of the {n_questions} questions, use memory_search or
     memory_retrieve with the question's concept — the semantic embedding
     should find your matching note even when the words differ.
  3. Answer.

Output the LAST {n_questions} lines of your response in EXACTLY:

Q01: <name>
Q02: <name>
...
Q{n_questions:02d}: <name>

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
    workdir = WORK_BASE / f"b9-{arm}-{ts}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    gt = prepare(workdir)

    total_bytes = sum(p.stat().st_size for p in workdir.glob("d*.md"))
    print(f"=== B9 ARM: {arm} ===")
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
    tmpl = PROMPT_TMPL_MEM if arm == "with_memory" else PROMPT_TMPL_NO_MEM
    prompt = tmpl.format(
        n_docs=gt["n_docs"], last=gt["n_docs"] - 1,
        mb=total_bytes / 1024 / 1024,
        n_questions=len(gt["questions"]),
        questions=questions_text,
    )

    options = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        effort="low",
        permission_mode="bypassPermissions",
        cwd=str(workdir),
        allowed_tools=allowed,
        mcp_servers=mcp_servers,
        max_turns=120,
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

    # Check whether memory was actually used
    notes_dir = workdir / ".memory-graph" / "notes"
    n_notes = sum(1 for _ in notes_dir.glob("*.md")) if notes_dir.is_dir() else 0
    scratch_files = [
        p.name for p in workdir.iterdir()
        if p.is_file() and p.name.endswith((".json", ".txt", ".csv"))
        and not p.name.startswith("d0") and p.name != "_ground_truth.json"
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
    print(f"B9 v2: {N_DOCS} docs / {N_QUESTIONS} paraphrased queries")
    print("=" * 64)
    no_mem = await run_arm("no_memory")
    with_mem = await run_arm("with_memory")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "b9_large_corpus.json").write_text(
        json.dumps({"no_memory": no_mem, "with_memory": with_mem}, indent=2)
    )
    print()
    print("FINAL")
    print(f"  no_memory   score={no_mem['score']}/{no_mem['total']}  cost=${no_mem['cost_usd'] or 0:.4f}  time={no_mem['seconds']}s  notes={no_mem['memory_notes']}")
    print(f"  with_memory score={with_mem['score']}/{with_mem['total']}  cost=${with_mem['cost_usd'] or 0:.4f}  time={with_mem['seconds']}s  notes={with_mem['memory_notes']}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
