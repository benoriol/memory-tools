"""B8: Semantic Q&A over a corpus, where answers are NOT guessable.

Setup: 30 design-decision documents about a fictional project where every
tool/choice/component has a made-up name (not a real datastore, not a real
framework). The questions describe the decisions semantically ("which
choice was driven by latency concerns?") but the ANSWER (the fictional
component name) can only be learned by reading the documents.

Both arms can in principle answer all 30 questions. The question is which
is more efficient when there are many semantic queries over a corpus.

Hypothesis: with_memory captures once + retrieves cheaply per question.
no_memory must either read all 30 files up front (lots of input tokens)
or re-scan per question.
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


# Fictional components. Each tuple: (id, prose, semantic_question, fictional_answer)
DECISIONS = [
    ("d01",
     "We adopted Quennel for the catalog service. The team debated Mvorra but "
     "rejected it because we needed strong transactional guarantees across the "
     "billing tables. Existing operational expertise also favored Quennel.",
     "Which catalog datastore was kept because of transactional guarantees?",
     "Quennel"),
    ("d02",
     "The image pipeline was rewritten on top of the Crispel runtime last "
     "quarter. The previous Slathe-based implementation was repeatedly missing "
     "the p95 latency target during traffic spikes, and profiling pointed at "
     "runtime contention.",
     "Which runtime now hosts the image pipeline (chosen over the previous one) "
     "because of tail-latency?",
     "Crispel"),
    ("d03",
     "Search uses Halberd, a sharded inverted index hosted on five nodes. We "
     "considered Ravenmark, the SaaS option, but its operational overhead and "
     "unit economics were judged unjustifiable for our team size.",
     "Which in-house tool was preferred over the SaaS Ravenmark for search?",
     "Halberd"),
    ("d04",
     "The mobile API gateway accepts both the Plumelay RPC dialect and the "
     "older Threnody REST surface. Keeping Threnody around was reluctant — "
     "old mobile clients we can't force-upgrade still depend on it.",
     "Which interface (gateway surface) was kept solely for backwards "
     "compatibility with old mobile clients?",
     "Threnody"),
    ("d05",
     "Tracing data goes through the Pyrethorn collector. Sampling is fixed at "
     "1%. We started at 100% but the Pyrethorn storage costs at full sampling "
     "exceeded the rest of the observability budget combined.",
     "Which collector is sampled at 1% to control cost?",
     "Pyrethorn"),
    ("d06",
     "The configuration store uses Veristone. We picked it for the strong "
     "consistency and watch-based change semantics — Coelibrant was considered "
     "but lacked the durability story.",
     "Which config-store was chosen for its consistency + watch semantics?",
     "Veristone"),
    ("d07",
     "Background jobs are dispatched via our in-house Folwark scheduler. "
     "Larkmount was evaluated; we rejected it because we needed precise "
     "per-tenant priority weighting that Larkmount's queue model couldn't express.",
     "Which in-house scheduler is used instead of the Larkmount option?",
     "Folwark"),
    ("d08",
     "Embedding generation runs on the Sondheim CPU cluster, not on GPUs. For "
     "our model size and throughput, the GPU cost was more than 4x the CPU "
     "cost for equivalent throughput.",
     "Which compute cluster handles embedding generation (chosen for cost)?",
     "Sondheim"),
    ("d09",
     "Authentication is centralized in the Praewyn service. We considered "
     "letting each microservice verify tokens locally, but token revocation "
     "was the requirement that pushed us to centralize on Praewyn.",
     "Which centralized service was driven by the token-revocation requirement?",
     "Praewyn"),
    ("d10",
     "Daily exports go directly to customer-owned Thurible buckets via "
     "cross-account roles. We rejected a pull-based API because customers "
     "wanted the data to land in their environment without integration work.",
     "Which destination type holds the daily exports for cross-account delivery?",
     "Thurible"),
    ("d11",
     "The frontend is built on Brindlewell. We rejected a pure-SPA approach "
     "because the public marketing pages need to be indexable and FCP "
     "mattered to the marketing team.",
     "Which frontend framework was chosen because of SEO + FCP concerns?",
     "Brindlewell"),
    ("d12",
     "We use Stelluna for inter-service messages, with one schema repo. The "
     "decision was made to avoid the schema drift we previously saw with "
     "ad-hoc Glanwood payloads.",
     "Which serialization format was chosen to combat schema drift?",
     "Stelluna"),
    ("d13",
     "Image storage uses the Thurible bucket family fronted by Mirepoix, the "
     "CDN edge. Mirepoix was added late, after we discovered hot images were "
     "fetched repeatedly from origin and egress costs ballooned.",
     "Which CDN was added later to address egress costs?",
     "Mirepoix"),
    ("d14",
     "Feature flags live in Pellinor. We considered building our own; the "
     "deciding factor was Pellinor's targeting DSL — building a comparable "
     "targeting language would have cost engineer-months.",
     "Which third-party service was chosen because its targeting DSL would "
     "be expensive to replicate?",
     "Pellinor"),
    ("d15",
     "All async work between services goes through Vexford. We considered "
     "Larkmount-MQ but Vexford's replay semantics and the retention story "
     "made it the obvious pick for analytics-adjacent workloads.",
     "Which message bus was chosen for replay + retention?",
     "Vexford"),
    ("d16",
     "The data warehouse is Karstmere. Heliodon was evaluated; Karstmere's "
     "pay-per-query pricing fit our spiky analytical workload better than "
     "Heliodon's committed-compute model.",
     "Which warehouse was chosen for pay-per-query economics?",
     "Karstmere"),
    ("d17",
     "Audit logs are stored in Verisade. The compliance team required a "
     "tamper-evident record for SOC2; Verisade's write-once-versioned mode "
     "with retention lock met that requirement.",
     "Which audit-log destination was chosen for compliance tamper-evidence?",
     "Verisade"),
    ("d18",
     "The Cinderwood analytics pipeline tolerates duplicate writes. The "
     "deduplication cost was deemed not worth the engineering effort because "
     "downstream aggregations are idempotent at the query layer.",
     "Which pipeline deliberately accepts duplicate writes as acceptable debt?",
     "Cinderwood"),
    ("d19",
     "Customer data is encrypted at rest with the Argentbridge BYOK scheme. "
     "This was added to win a specific enterprise deal; the implementation "
     "cost was high but the contract value justified it.",
     "Which BYOK scheme was added to land an enterprise contract?",
     "Argentbridge"),
    ("d20",
     "We deploy via the Outhewn blue-green system rather than the Pellinor "
     "canary it replaced. Pellinor canary was tried first but our traffic "
     "patterns are too bursty for percentage-based shifting to be meaningful.",
     "Which deploy system replaced the canary system that bursty traffic "
     "made ineffective?",
     "Outhewn"),
    ("d21",
     "Internal admin tooling is a Sundappur app. Build-vs-buy went buy because "
     "the admin features change weekly and internal users tolerate the "
     "Sundappur UX trade-offs.",
     "Which low-code admin platform was chosen because the use case changes "
     "frequently?",
     "Sundappur"),
    ("d22",
     "The session store uses Coelibrant. We chose Coelibrant for raw "
     "throughput and were comfortable with its in-memory model because "
     "sessions are reconstructible from auth tokens if a node fails.",
     "Which in-memory store was tolerated because state is reconstructible?",
     "Coelibrant"),
    ("d23",
     "Log search uses Cathlock. We picked Cathlock over Ravenmark because of "
     "Ravenmark's restrictive license — we deploy in customer environments "
     "and the license complicated that.",
     "Which log-search tool was chosen primarily for licensing reasons?",
     "Cathlock"),
    ("d24",
     "Rate limiting is centralized at the Mirepoix edge rather than in each "
     "service. The decision came after local rate-limiters couldn't see "
     "global request volume and produced thundering-herd issues.",
     "At which layer was rate limiting re-centralized?",
     "Mirepoix"),
    ("d25",
     "Frontend errors are reported via Argo-Stelloth. We rejected building "
     "our own because the stacktrace-deobfuscation pipeline alone would have "
     "been a multi-month project.",
     "Which error reporter was chosen because deobfuscation would be too "
     "expensive to build?",
     "Argo-Stelloth"),
    ("d26",
     "We keep all schemas in the Threpwood monorepo. The previous Glanwood "
     "polyglot-repo approach was abandoned after two quarters of integration "
     "pain whenever cross-service schema changes rolled out in the wrong order.",
     "Which monorepo replaced the abandoned Glanwood polyglot approach?",
     "Threpwood"),
    ("d27",
     "Code review uses the Halberdsworth two-approvals rule for production "
     "code and one approval for tests. The asymmetry exists because test "
     "review lag was dropping coverage, which the team judged a worse outcome.",
     "Which review policy was made asymmetric to avoid coverage erosion?",
     "Halberdsworth"),
    ("d28",
     "We don't use a service mesh. Larkmount-Mesh was evaluated; the "
     "operational overhead exceeded the benefits given our modest number of "
     "services.",
     "Which mesh option was declined because of operational overhead?",
     "Larkmount-Mesh"),
    ("d29",
     "Database schema changes go through the Inglemoore migration framework, "
     "which requires backwards compatibility for at least one release. The "
     "rule was added after a specific non-compat migration locked out the "
     "rollback path.",
     "Which migration framework enforces the one-release backwards-compat rule?",
     "Inglemoore"),
    ("d30",
     "The legacy Threnody v1 surface will be sunset on the publicly announced "
     "date. The decision came down because supporting Threnody v1 required "
     "maintaining a separate codepath whose test coverage had degraded.",
     "Which legacy surface is being sunset because of test-coverage degradation?",
     "Threnody"),
]


def prepare(workdir: Path) -> dict[str, Any]:
    workdir.mkdir(parents=True, exist_ok=True)
    for did, prose, _, _ in DECISIONS:
        (workdir / f"{did}.md").write_text(f"# Decision: {did}\n\n{prose}\n")
    truth = {did: key for did, _, _, key in DECISIONS}
    questions = [(f"Q{i + 1:02d}", q, did, key) for i, (did, _, q, key) in enumerate(DECISIONS)]
    return {"truth": truth, "questions": questions, "n_decisions": len(DECISIONS)}


PROMPT_TMPL = """\
This directory contains {n_decisions} markdown files named d01.md ... d30.md.
Each file describes a single architectural decision for a fictional project.
All tool / framework / component names in these documents are MADE UP — you
cannot guess them from prior knowledge; you must read the documents.

You will be asked {n_questions} questions about the decisions. Each question
describes a decision SEMANTICALLY (not by name). Your job is to answer with
the made-up component name that the document identifies.

Use whatever approach you prefer (Read, Grep, memory tools if available).
Pick the approach you think will be the most efficient.

Answer all questions. Output the LAST {n_questions} lines of your response in
EXACTLY this format:

Q01: <component-name>
Q02: <component-name>
...
Q{n_questions:02d}: <component-name>

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
    workdir = WORK_BASE / f"b8-{arm}-{ts}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    gt = prepare(workdir)

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

    n_questions = len(gt["questions"])
    questions_text = "\n".join(f"{qid}: {q}" for qid, q, _, _ in gt["questions"])
    prompt = PROMPT_TMPL.format(
        n_decisions=gt["n_decisions"],
        n_questions=n_questions,
        questions=questions_text,
    )

    options = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        effort="low",
        permission_mode="bypassPermissions",
        cwd=str(workdir),
        allowed_tools=allowed,
        mcp_servers=mcp_servers,
        max_turns=80,
    )

    print(f"=== B8 ARM: {arm} ===")
    print(f"  workdir: {workdir}")
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

    print(f"  time: {seconds}s  cost: ${cost or 0:.4f}  score: {hits}/{n_questions}")
    print(f"  usage: in={usage.get('input_tokens', 0)} out={usage.get('output_tokens', 0)} "
          f"cache_read={usage.get('cache_read_input_tokens', 0)} "
          f"cache_create={usage.get('cache_creation_input_tokens', 0)}")
    return {
        "arm": arm,
        "score": hits,
        "total": n_questions,
        "cost_usd": cost,
        "seconds": seconds,
        "usage": usage,
        "per_question": per_q,
        "workdir": str(workdir),
    }


async def main_async() -> int:
    print("=" * 64)
    print("B8: Semantic Q&A over 30 fictional-component decisions")
    print("=" * 64)
    no_mem = await run_arm("no_memory")
    with_mem = await run_arm("with_memory")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "b8_semantic_qa.json").write_text(
        json.dumps({"no_memory": no_mem, "with_memory": with_mem}, indent=2)
    )
    print()
    print("FINAL")
    print(f"  no_memory   score={no_mem['score']}/{no_mem['total']}  cost=${no_mem['cost_usd'] or 0:.4f}  time={no_mem['seconds']}s")
    print(f"  with_memory score={with_mem['score']}/{with_mem['total']}  cost=${with_mem['cost_usd'] or 0:.4f}  time={with_mem['seconds']}s")
    print(f"  cost delta: ${(with_mem['cost_usd'] or 0) - (no_mem['cost_usd'] or 0):+.4f}")
    print(f"  time delta: {with_mem['seconds'] - no_mem['seconds']:+.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
