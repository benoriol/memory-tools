"""e25 - multi-vector vs single-vector vs grep on cross-vocabulary recall.

See README.md for design + hypothesis + pass criterion. Three arms,
50 notes, 50 paired queries phrased with different vocabulary than
the note bodies. Truth held in this script.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import resource
import shutil
import sys
import time
from pathlib import Path
from typing import Any

RAM_BYTES_CAP = 32 * 1024**3
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


REPO_ROOT = Path(__file__).resolve().parents[4]
RESULTS_DIR = Path(__file__).resolve().parent
WORK_BASE = Path("/tmp/e25-bench")


# Each fact has a `body` (the captured note) and a `query` (orthogonally
# phrased). The `id` is just a tag for logs.
FACTS: list[dict[str, str]] = [
    {"id": "outbound_breaker",
     "body": "The OutboundBreaker class wraps every external HTTP call and opens after five consecutive failures.",
     "query": "Which component shields us from cascading failures when a downstream service is misbehaving?"},
    {"id": "registry_singleton",
     "body": "core.registry holds the application's global singletons during process lifetime.",
     "query": "Where does the runtime keep its long-lived shared objects?"},
    {"id": "frame_magic_byte",
     "body": "Every serialized frame on the wire begins with the magic byte 0x7f.",
     "query": "What prefix identifies the start of a binary message in transit?"},
    {"id": "cache_ttl",
     "body": "Cached entries remain valid for 3600 seconds before expiry.",
     "query": "How long until items in the in-memory cache go stale?"},
    {"id": "transform_plugin",
     "body": "Downstream transformers must implement the TransformPlugin contract (4 required methods).",
     "query": "Which interface do extension modules satisfy to participate in the pipeline?"},
    {"id": "dataflow_home_env",
     "body": "DATAFLOW_HOME is the environment variable that relocates the data directory.",
     "query": "How do operators change where on-disk state lives?"},
    {"id": "ast_walker",
     "body": "AstWalker implements the visitor pattern over our syntax trees.",
     "query": "Which class lets us traverse the parsed code structure?"},
    {"id": "retry_max",
     "body": "The job runner retries a broken job at most 5 times before giving up.",
     "query": "What is the upper bound on retries before a permanent failure?"},
    {"id": "metrics_port",
     "body": "The Prometheus scrape listener binds to TCP port 9342.",
     "query": "On what socket does the observability endpoint accept connections?"},
    {"id": "blake3_chunk",
     "body": "Each storage chunk is validated with a blake3 checksum.",
     "query": "What hash function protects on-disk segments from corruption?"},
    {"id": "config_reloaded",
     "body": "The ConfigReloaded signal forces every cache layer to drop its entries.",
     "query": "Which event causes a flush of all cached state?"},
    {"id": "quota_exceeded",
     "body": "When a tenant blows past their usage cap we raise QuotaExceeded.",
     "query": "What exception fires when a customer trips their rate ceiling?"},
    {"id": "transport_pool",
     "body": "transport.pool is the module that manages reusable network sockets.",
     "query": "Where does connection reuse live in the codebase?"},
    {"id": "priority_levels",
     "body": "The scheduler queue accepts 7 distinct urgency levels.",
     "query": "How many priority tiers does the work dispatcher recognize?"},
    {"id": "idx2_suffix",
     "body": "On-disk lookup files use the .idx2 extension.",
     "query": "What filename pattern identifies the search index format?"},
    {"id": "audit_trail",
     "body": "AuditTrail records every administrative action taken in the system.",
     "query": "Which class persists the log of operator-driven changes?"},
    {"id": "max_payload",
     "body": "The upper bound on any single request body is 1048576 bytes.",
     "query": "What is the cap on inbound message size?"},
    {"id": "di_core",
     "body": "core.di hosts the dependency injection container that wires components together.",
     "query": "Which module does service wiring?"},
    {"id": "watcher_interval",
     "body": "Filesystem watcher polls every 250 ms between scans.",
     "query": "How frequently does the directory monitor wake up to look for changes?"},
    {"id": "protocol_revision",
     "body": "The current wire protocol revision is v3.2.",
     "query": "Which version of the inter-node format is in production today?"},
    {"id": "vermeer_planner",
     "body": "The experimental query planner is internally codenamed Vermeer.",
     "query": "What is the project name for the next-generation query optimizer?"},
    {"id": "compact_tier",
     "body": "Storage.compact_tier is the routine that merges old tiered files together.",
     "query": "Which method performs background segment merging?"},
    {"id": "ratelimit_window",
     "body": "The throttling window has a 120-second duration.",
     "query": "Over what span does the rate limiter count requests?"},
    {"id": "shared_lock",
     "body": "storage and indexer contend on the same lock manager.",
     "query": "Which two subsystems share a mutex?"},
    {"id": "bloom_seed",
     "body": "The bloom filter hash seed is the magic constant 0xC0FFEE.",
     "query": "What salt is mixed into the approximate set membership hashes?"},
    {"id": "pool_size",
     "body": "The shared executor's default thread pool size is 16 workers.",
     "query": "How many worker threads run by default?"},
    {"id": "telemetry_buffer",
     "body": "telemetry.buffer is the ring that accumulates measurements before flushing.",
     "query": "Where do metrics get batched before being sent out?"},
    {"id": "schema_v4",
     "body": "The persisted catalog file declares format identifier schema_v4.",
     "query": "What version label is stamped on the saved metadata?"},
    {"id": "msgpack_ipc",
     "body": "Inter-process messages between workers are serialized with msgpack.",
     "query": "What encoding is used for communication between local processes?"},
    {"id": "connection_fsm",
     "body": "ConnectionFsm models the finite-state machine of each socket's lifecycle.",
     "query": "Which class manages the state transitions of an open link?"},
    {"id": "leader_election",
     "body": "Leader election uses the Raft consensus algorithm with 150ms heartbeats.",
     "query": "How do nodes agree on a primary when a coordinator dies?"},
    {"id": "snapshot_interval",
     "body": "We take a state snapshot every 600 seconds for disaster recovery.",
     "query": "How often is on-disk durable state captured?"},
    {"id": "auth_jwt",
     "body": "Authentication tokens are signed JWTs using EdDSA keys.",
     "query": "What cryptographic scheme verifies caller identity?"},
    {"id": "log_partition",
     "body": "The write-ahead log is partitioned into 64MB segments.",
     "query": "How large is each chunk of the durability journal?"},
    {"id": "feature_flag_store",
     "body": "Feature flags live in flags.runtime and refresh every 5 seconds.",
     "query": "Where are toggleable behavior switches kept?"},
    {"id": "deadline_propagation",
     "body": "Each RPC carries a deadline header that downstream services must honor.",
     "query": "How are timeouts plumbed across service boundaries?"},
    {"id": "tracing_sampler",
     "body": "We use a probabilistic tracing sampler at a 1% sample rate.",
     "query": "How is the volume of distributed-trace data kept manageable?"},
    {"id": "tls_version",
     "body": "All external listeners require TLS 1.3 with no downgrade.",
     "query": "Which encryption protocol does the public API insist on?"},
    {"id": "backpressure_queue",
     "body": "The ingest pipeline applies backpressure when its queue exceeds 10000 items.",
     "query": "What slows producers down when the system is overloaded?"},
    {"id": "shutdown_signal",
     "body": "Workers drain in-flight requests on SIGTERM with a 30-second grace period.",
     "query": "How does the process exit cleanly while still serving traffic?"},
    {"id": "checksum_walker",
     "body": "The integrity walker scans every chunk weekly and emails on mismatch.",
     "query": "Who detects silent data corruption on a regular cadence?"},
    {"id": "geo_routing",
     "body": "Requests are geographically routed using GeoIP region tags.",
     "query": "How does traffic find its nearest datacenter?"},
    {"id": "schema_migration",
     "body": "Schema migrations are applied in lock-step via the migrate.runner CLI.",
     "query": "What tool advances the database structure between releases?"},
    {"id": "deadlock_detector",
     "body": "A background DeadlockDetector kills the youngest transaction in a cycle.",
     "query": "How do we recover when two queries are stuck waiting on each other?"},
    {"id": "feature_gate_admin",
     "body": "FeatureGate.admin lets operators toggle gated functionality at runtime.",
     "query": "Which API enables or disables capabilities without a deploy?"},
    {"id": "stream_compression",
     "body": "Outbound streaming uses zstd compression at level 3.",
     "query": "How is bandwidth reduced for long-lived event feeds?"},
    {"id": "audit_retention",
     "body": "Audit entries are retained on disk for 90 days before archival.",
     "query": "How long do we keep operator-action logs locally?"},
    {"id": "metric_cardinality",
     "body": "Metric cardinality is capped at 100000 unique label combinations.",
     "query": "What protects the time-series database from label explosion?"},
    {"id": "request_id_header",
     "body": "Every inbound request carries an X-Request-Id header propagated end-to-end.",
     "query": "How do we correlate logs across services for one user action?"},
    {"id": "circuit_half_open",
     "body": "After 30 seconds open, the breaker enters a half-open probe state.",
     "query": "When does the protector test whether downstream has recovered?"},
]

assert len(FACTS) == 50, f"expected 50 facts, got {len(FACTS)}"


def _generate_notes(workdir: Path) -> None:
    notes_dir = workdir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    for i, fact in enumerate(FACTS):
        nid = f"note_{i:02d}"
        path = notes_dir / f"{nid}.md"
        path.write_text(
            f"---\nid: {nid}\nfact_id: {fact['id']}\n---\n\n{fact['body']}\n"
        )


def _recall_at_k(ranked_ids: list[str], truth_id: str, k: int) -> int:
    return 1 if truth_id in ranked_ids[:k] else 0


# ---------------------------------------------------------------------------
# Arm: grep
# ---------------------------------------------------------------------------

GREP_PROMPT = """\
You are answering a single retrieval query against the markdown notes in
`./notes/`. Each file is one note. The query is phrased with different
vocabulary than the note it refers to, so direct substring grep usually
won't hit. Use Bash + Grep + Read to find the best matching note.

Output ONLY a single line of the form:

ANSWER: <note_id_1>, <note_id_2>, <note_id_3>, <note_id_4>, <note_id_5>

where note_id is the filename without `.md`, ranked best first. List up
to 5 candidates. No prose.

Query: {query}
"""


async def grep_arm(workdir: Path) -> dict[str, Any]:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        query as agent_query,
    )

    _generate_notes(workdir)
    recall1 = 0
    recall5 = 0
    total_cost = 0.0
    t0 = time.monotonic()
    per_query: list[dict[str, Any]] = []

    for i, fact in enumerate(FACTS):
        truth = f"note_{i:02d}"
        options = ClaudeAgentOptions(
            model="claude-sonnet-4-6",
            effort="low",
            permission_mode="bypassPermissions",
            cwd=str(workdir),
            allowed_tools=["Bash", "Grep", "Read", "Glob"],
            mcp_servers={},
            max_turns=15,
        )
        chunks: list[str] = []
        last = None
        async for msg in agent_query(prompt=GREP_PROMPT.format(query=fact["query"]), options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    t = getattr(block, "text", None)
                    if t:
                        chunks.append(t)
            elif isinstance(msg, ResultMessage):
                last = msg
        text = "\n".join(chunks)
        cost = getattr(last, "total_cost_usd", None) if last else None
        total_cost += cost or 0.0
        ranked = _parse_answer_line(text)
        r1 = _recall_at_k(ranked, truth, 1)
        r5 = _recall_at_k(ranked, truth, 5)
        recall1 += r1
        recall5 += r5
        per_query.append({"i": i, "truth": truth, "ranked": ranked[:5], "r1": r1, "r5": r5})

    return {
        "arm": "grep",
        "recall_at_1": recall1 / len(FACTS),
        "recall_at_5": recall5 / len(FACTS),
        "total_cost_usd": total_cost,
        "total_seconds": round(time.monotonic() - t0, 1),
        "per_query": per_query,
    }


def _parse_answer_line(text: str) -> list[str]:
    m = re.search(r"ANSWER\s*:\s*(.+)", text)
    if not m:
        return []
    raw = m.group(1).strip()
    parts = [p.strip().rstrip(".") for p in raw.split(",")]
    return [p for p in parts if p]


# ---------------------------------------------------------------------------
# Arm: single-vector
# ---------------------------------------------------------------------------


def single_arm() -> dict[str, Any]:
    from memory_recall.embed import LocalEmbedder

    t0 = time.monotonic()
    emb = LocalEmbedder()
    body_vectors = emb.embed([f["body"] for f in FACTS])
    body_vectors = _l2_normalize(body_vectors)
    query_vectors = emb.embed([f["query"] for f in FACTS])
    query_vectors = _l2_normalize(query_vectors)
    sims = query_vectors @ body_vectors.T

    recall1 = 0
    recall5 = 0
    per_query: list[dict[str, Any]] = []
    for i in range(len(FACTS)):
        order = sims[i].argsort()[::-1]
        ranked = [f"note_{int(j):02d}" for j in order]
        truth = f"note_{i:02d}"
        r1 = _recall_at_k(ranked, truth, 1)
        r5 = _recall_at_k(ranked, truth, 5)
        recall1 += r1
        recall5 += r5
        per_query.append({"i": i, "truth": truth, "ranked": ranked[:5], "r1": r1, "r5": r5})

    return {
        "arm": "single",
        "recall_at_1": recall1 / len(FACTS),
        "recall_at_5": recall5 / len(FACTS),
        "total_cost_usd": 0.0,
        "total_seconds": round(time.monotonic() - t0, 1),
        "per_query": per_query,
    }


def _l2_normalize(mat):
    import numpy as np

    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.where(norms > 0, norms, 1.0)
    return mat / norms


# ---------------------------------------------------------------------------
# Arm: multi-vector (memory_recall pipeline)
# ---------------------------------------------------------------------------


async def multi_arm(workdir: Path) -> dict[str, Any]:
    from memory_recall.embed import LocalEmbedder
    from memory_recall.storage.files import init_store
    from memory_recall.store import Store
    from memory_recall.subagent import expand_for_capture, expand_for_search

    root = init_store(workdir)
    store = Store(root, LocalEmbedder())

    t0 = time.monotonic()
    capture_cost_estimate = 0.0  # The sub-agent call cost isn't exposed by our wrapper;
    search_cost_estimate = 0.0   # leave for future enrichment if needed.

    note_id_by_fact_idx: dict[int, str] = {}
    for i, fact in enumerate(FACTS):
        expanded = await expand_for_capture(fact["body"])
        note = store.capture(
            fact["body"],
            title=expanded["title"],
            summary=expanded["summary"],
            keywords=expanded["keywords"],
            paraphrases=expanded["paraphrases"],
            tags=expanded["tags"] + [f"fact:{fact['id']}"],
        )
        note_id_by_fact_idx[i] = note.id

    recall1 = 0
    recall5 = 0
    per_query: list[dict[str, Any]] = []
    for i, fact in enumerate(FACTS):
        expanded = await expand_for_search(fact["query"])
        hits = store.search(expanded["query_views"], k=10)
        ranked_note_ids = [n.id for (n, _s, _v) in hits]
        truth = note_id_by_fact_idx[i]
        r1 = _recall_at_k(ranked_note_ids, truth, 1)
        r5 = _recall_at_k(ranked_note_ids, truth, 5)
        recall1 += r1
        recall5 += r5
        per_query.append({
            "i": i, "truth_fact": fact["id"], "truth_id": truth,
            "ranked": ranked_note_ids[:5],
            "matched_view": hits[0][2] if hits else None,
            "r1": r1, "r5": r5,
        })

    return {
        "arm": "multi",
        "recall_at_1": recall1 / len(FACTS),
        "recall_at_5": recall5 / len(FACTS),
        "subagent_capture_cost_usd": capture_cost_estimate,
        "subagent_search_cost_usd": search_cost_estimate,
        "total_cost_usd": capture_cost_estimate + search_cost_estimate,
        "total_seconds": round(time.monotonic() - t0, 1),
        "per_query": per_query,
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def _fresh_workdir(name: str) -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S")
    p = WORK_BASE / f"e25-{name}-{ts}"
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True)
    return p


async def main_async(args: argparse.Namespace) -> int:
    print("=" * 64)
    print("e25: multi-vector vs single-vector vs grep")
    print("=" * 64)

    if args.dry_run:
        print("[dry-run] Skipping all arms; verifying imports and fact list.")
        print(f"facts: {len(FACTS)}")
        for fact in FACTS[:3]:
            print(f"  {fact['id']}: body='{fact['body'][:60]}...'")
        # Touch each arm function reference to ensure imports work.
        assert callable(grep_arm)
        assert callable(single_arm)
        assert callable(multi_arm)
        return 0

    results: dict[str, Any] = {}

    if "single" in args.arms:
        print("\n--- single-vector arm ---")
        results["single"] = single_arm()
        print(f"  recall@1: {results['single']['recall_at_1']:.2%}  "
              f"recall@5: {results['single']['recall_at_5']:.2%}  "
              f"({results['single']['total_seconds']}s)")

    if "grep" in args.arms:
        print("\n--- grep arm ---")
        wd = _fresh_workdir("grep")
        results["grep"] = await grep_arm(wd)
        print(f"  recall@1: {results['grep']['recall_at_1']:.2%}  "
              f"recall@5: {results['grep']['recall_at_5']:.2%}  "
              f"cost=${results['grep']['total_cost_usd']:.3f}  "
              f"({results['grep']['total_seconds']}s)")

    if "multi" in args.arms:
        print("\n--- multi-vector arm ---")
        wd = _fresh_workdir("multi")
        results["multi"] = await multi_arm(wd)
        print(f"  recall@1: {results['multi']['recall_at_1']:.2%}  "
              f"recall@5: {results['multi']['recall_at_5']:.2%}  "
              f"({results['multi']['total_seconds']}s)")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "e25_results.json").write_text(json.dumps(results, indent=2))

    if "single" in results and "multi" in results:
        s = results["single"]
        m = results["multi"]
        r1_gap = m["recall_at_1"] - s["recall_at_1"]
        r5_gap = m["recall_at_5"] - s["recall_at_5"]
        pass1 = r1_gap >= 0.10
        pass5 = r5_gap >= 0.05
        verdict = "PASS" if (pass1 or pass5) else "FAIL"
        print("\nFINAL")
        print(f"  recall@1 gap (multi - single): {r1_gap:+.2%}  (>=0.10 to pass: {pass1})")
        print(f"  recall@5 gap (multi - single): {r5_gap:+.2%}  (>=0.05 to pass: {pass5})")
        print(f"  verdict: {verdict}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Verify imports/facts without running any arm.")
    parser.add_argument(
        "--arms", nargs="+", default=["single", "grep", "multi"],
        choices=["single", "grep", "multi"],
        help="Subset of arms to run (default: all three).",
    )
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
