"""Build a synthetic but valid memory graph for retrieval benchmarks.

Domain: a fake software-product team called "Mango" that built a
multi-service backend over 18 months. The graph captures their
observations, experiments, decisions, lessons, incidents, principles,
user_said constraints, and a few superseded older choices.

The graph is deterministic — same seed produces the same ids and
content — so retrieval tasks can reference specific notes by id.

Usage:
    python -m demos.eval.build_graph /path/to/empty/.memory-graph/dir [--n 150]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

# Make the deterministic ULID generator produce stable ids across runs.
import os
os.environ.setdefault("MG_SEED", "1")

import random

# ---------------------------------------------------------------------------

PROJECT_INTRO = (
    "Synthetic memory graph for the 'Mango' team's backend project. "
    "Three services (auth, billing, ingest), 18 months of history."
)

# Each tuple: (short_label, title, kind, summary, body, tags, abstract_parent_idx)
# abstract_parent_idx points into the same list to draw an `abstracts` edge
# FROM the parent (more abstract) TO this child. None means no parent.
@dataclass
class Seed:
    short_label: str
    title: str
    kind: str
    summary: str
    body: str
    tags: list[str]
    abstracts_to: list[int]   # indices of children this one ABSTRACTS
    related_to: list[int] = None      # lateral edges
    supersedes: int | None = None     # index of older note this supersedes


# ---------------------------------------------------------------------------
# AUTH service — decisions, lessons, incidents around login + token storage
# ---------------------------------------------------------------------------

AUTH_SEEDS: list[Seed] = [
    # 0  user_said
    Seed("must allow SSO",
         "User requirement: SSO is mandatory for enterprise customers",
         "user_said",
         "Enterprise contracts require SAML/OIDC SSO. No password-only paths for enterprise tenants.",
         "Stated during the Q2 enterprise contract review. Affects auth service design end-to-end.",
         ["auth", "user_said"],
         abstracts_to=[]),
    # 1
    Seed("password hashing",
         "Decision: use Argon2id for password hashing",
         "decision",
         "Chose Argon2id (m=64MB, t=3, p=4) over bcrypt for new password hashes.",
         "Argon2id won out for memory-hardness against GPU attacks. Bcrypt remains acceptable for legacy hashes; we lazy-migrate on next login.",
         ["auth", "security"],
         abstracts_to=[]),
    # 2
    Seed("session token storage",
         "Decision: store session tokens in HttpOnly+Secure cookies",
         "decision",
         "Browser sessions: HttpOnly+Secure+SameSite=Lax cookies. Mobile: bearer in Authorization header.",
         "JWT inside HttpOnly cookie for browser; refresh via /auth/refresh. Decision driven by XSS resistance.",
         ["auth", "security", "cookies"],
         abstracts_to=[]),
    # 3
    Seed("rotate refresh tokens",
         "Decision: rotate refresh tokens on every use",
         "decision",
         "Refresh tokens are single-use; each refresh issues a new one and invalidates the prior.",
         "Detects refresh-token theft when the old token is reused. Implemented via a per-user generation counter.",
         ["auth", "security"],
         abstracts_to=[]),
    # 4
    Seed("Argon2id calibration",
         "Experiment: Argon2id parameter calibration on prod hardware",
         "experiment",
         "Tested m=32/64/128MB, t=2/3/4. Settled on m=64, t=3 for 250ms median hash time.",
         "Ran on production auth-1 (8-core Xeon, 32GB). 250ms was the target chosen to balance UX and brute-force cost.",
         ["auth", "argon2", "experiment"],
         abstracts_to=[]),
    # 5
    Seed("HMAC for csrf",
         "Lesson: SameSite=Lax is NOT enough — keep CSRF tokens",
         "lesson",
         "Found a top-level navigation POST vector that bypasses SameSite=Lax. CSRF tokens remain required.",
         "Source: pen-test report Q3. The fix: HMAC-signed double-submit cookie for state-changing requests.",
         ["auth", "security", "csrf"],
         abstracts_to=[]),
    # 6
    Seed("token leak incident",
         "Incident: refresh token leaked via referer header to third-party JS",
         "incident",
         "On 2025-09-14 a refresh token was sent in Referer when /auth/refresh was hit from a redirect page that included third-party analytics JS.",
         "Root cause: refresh endpoint accepted GET as well as POST; navigating GET attaches Referer. Fix: refresh is POST-only, plus Referrer-Policy: no-referrer-when-downgrade enforced.",
         ["auth", "incident", "leak"],
         abstracts_to=[]),
    # 7
    Seed("MFA enrollment friction",
         "Lesson: forcing MFA on every login causes churn",
         "lesson",
         "Forcing MFA on every login caused a 12% drop in DAU. Switched to remember-device for 30 days.",
         "Source: A/B test in Oct 2025. Trust the device cookie if it has been MFA-verified within 30 days; require fresh MFA on suspicious context (new geo, new device).",
         ["auth", "mfa", "ux"],
         abstracts_to=[]),
    # 8  PRINCIPLE
    Seed("defense in depth",
         "Principle: defense in depth — never rely on one control",
         "principle",
         "No single security control is sufficient. SameSite, CSRF tokens, Origin checks, and Referrer-Policy each catch different attack classes.",
         "Articulated after the token-leak incident. Every state-changing endpoint should have at least two independent controls.",
         ["auth", "security", "principle"],
         abstracts_to=[5, 6]),   # abstracts SameSite-lesson and token-leak-incident
    # 9
    Seed("bcrypt legacy path",
         "Decision (superseded): bcrypt for all new passwords",
         "decision",
         "Initial decision in 2024 to use bcrypt cost=12.",
         "Outgrown by GPU advances + Argon2 maturity; superseded by note 1.",
         ["auth", "security", "legacy"],
         abstracts_to=[]),
    # 10  (10 supersedes 9)
    Seed("session ttl tuning",
         "Experiment: session TTL sweep, 1h vs 8h vs 24h",
         "experiment",
         "Tested session TTLs of 1h, 8h, 24h. 8h best balance of security + UX.",
         "Shorter forced re-auth on long sessions; longer increased risk of token theft. 8h with sliding refresh chosen.",
         ["auth", "session", "experiment"],
         abstracts_to=[]),
    # 11
    Seed("forced logout race",
         "Incident: forced-logout race condition during password change",
         "incident",
         "Password change didn't invalidate other active sessions consistently. Fixed by bumping user.session_generation on password change.",
         "Took two days to diagnose. The flaky test was actually telling the truth; we ignored it. See lesson note about flaky tests.",
         ["auth", "incident"],
         abstracts_to=[]),
    # 12  LESSON
    Seed("flaky tests reveal bugs",
         "Lesson: a flaky test is often a real concurrency bug",
         "lesson",
         "Three of the last four 'flaky' tests we silenced turned out to be real race conditions.",
         "Standing policy: a test that fails >2 times in a quarter cannot be silenced without a tracked investigation.",
         ["testing", "concurrency", "lesson"],
         abstracts_to=[11]),
]

# ---------------------------------------------------------------------------
# BILLING service
# ---------------------------------------------------------------------------

BILLING_SEEDS: list[Seed] = [
    # 13 user_said
    Seed("no SaaS for billing",
         "User constraint: billing must not depend on a SaaS vendor",
         "user_said",
         "Cannot use Stripe Billing / Recurly / etc. — must own the billing engine in-house.",
         "Stated explicitly by the founder in the kickoff. Allowed: payment processor (Stripe/Adyen), but invoicing + subscriptions must be ours.",
         ["billing", "user_said"],
         abstracts_to=[]),
    # 14
    Seed("Postgres for billing",
         "Decision: Postgres as the billing system of record",
         "decision",
         "Postgres 16 with row-level locking for invoice generation. ACID needed for financial correctness.",
         "Rejected NoSQL options because reconciliation across mixed currencies is much harder there.",
         ["billing", "database"],
         abstracts_to=[]),
    # 15
    Seed("decimal money",
         "Decision: store money as integer minor units",
         "decision",
         "All monetary amounts stored as Postgres BIGINT in minor units (cents, pence). No FLOAT, no DECIMAL.",
         "Decimal arithmetic is slower; integers are exact. Currency code stored adjacent for unit interpretation.",
         ["billing", "money", "schema"],
         abstracts_to=[]),
    # 16
    Seed("invoice double-charge",
         "Incident: double-charged invoice during retry storm",
         "incident",
         "On 2025-11-02 ~30 customers were double-charged when the payment gateway timed out and our worker retried without idempotency.",
         "Refunded all affected customers within 24h. Root cause: missing idempotency key on the charge call. Fix: use the invoice id as the idempotency key.",
         ["billing", "incident", "payments"],
         abstracts_to=[]),
    # 17  PRINCIPLE
    Seed("idempotency keys",
         "Principle: every external mutation must have an idempotency key",
         "principle",
         "All calls to payment gateways, email senders, and webhooks downstream MUST send an idempotency key tied to the business event.",
         "Generalized from the double-charge incident; applies to all external mutations, not just payments.",
         ["billing", "principle", "idempotency"],
         abstracts_to=[16]),
    # 18
    Seed("annual vs monthly",
         "Experiment: annual discount affects churn",
         "experiment",
         "12-month plans with 17% discount cut churn by 38% vs monthly plans.",
         "Sample: 600 self-serve accounts over 6 months. Effect strongest on tiers below $200/mo.",
         ["billing", "churn", "experiment"],
         abstracts_to=[]),
    # 19
    Seed("proration policy",
         "Decision: mid-cycle plan changes prorate linearly",
         "decision",
         "Upgrades charge the prorated delta immediately; downgrades credit on next cycle. No ad-hoc adjustments.",
         "Customer-support unhappy with downgrade timing; engineering unhappy with ad-hoc adjustments. Compromise documented in the billing policy doc.",
         ["billing", "policy"],
         abstracts_to=[]),
    # 20
    Seed("tax calc outsourced",
         "Decision: outsource sales tax to TaxJar",
         "decision",
         "Tax computation is delegated to TaxJar. Local fallback table for US-only customers in case the integration is down.",
         "Tax jurisdictions are too varied to maintain in-house. Acceptable to use a SaaS for this because the founder's no-SaaS rule applies to billing engine, not tax helpers.",
         ["billing", "tax"],
         abstracts_to=[]),
    # 21
    Seed("currency conversion",
         "Lesson: convert at invoice issuance, not payment",
         "lesson",
         "Locking exchange rates at invoice issuance avoids disputes when payment lags by days/weeks.",
         "Customer disputed an invoice because the exchange rate moved 3% between invoice and payment. Policy now: rate snapshot stored on the invoice row.",
         ["billing", "currency", "lesson"],
         abstracts_to=[]),
    # 22
    Seed("dunning ladder",
         "Decision: 3-step dunning ladder on failed payment",
         "decision",
         "On payment failure: retry at +1d (smart-retry), +3d (with email), +7d (suspend service).",
         "Replaces the old 'retry 5x in 24h' approach which hammered customers.",
         ["billing", "dunning"],
         abstracts_to=[]),
    # 23
    Seed("dunning v1 retired",
         "Decision (superseded): retry payment 5x in 24h",
         "decision",
         "Original (2024) approach: brute retry. Superseded by note 22.",
         "Was generating customer complaints; replaced with the 3-step ladder.",
         ["billing", "dunning", "legacy"],
         abstracts_to=[]),
    # 24
    Seed("free trial abuse",
         "Incident: free-trial abuse via disposable email domains",
         "incident",
         "Single user created 412 free-trial accounts via mailinator-style domains. Burned ~$800 of compute.",
         "Fix: block disposable email domains at signup; rate-limit free-trial accounts per IP and per credit-card BIN.",
         ["billing", "incident", "abuse"],
         abstracts_to=[]),
    # 25
    Seed("ingest billing model",
         "Decision: usage-based billing for ingest API",
         "decision",
         "Ingest priced per million events with bundled monthly allowance. Overage billed at end of month.",
         "Driven by user feedback that flat tiers were either too expensive (low volume) or too cheap (high volume).",
         ["billing", "ingest"],
         abstracts_to=[]),
    # 26  LESSON
    Seed("reconciliation hard",
         "Lesson: reconciliation across systems is much harder than you think",
         "lesson",
         "Every 'simple' reconciliation across payment processor and our DB took 3-5x the estimated effort.",
         "Allocate triple the budget for any reconciliation feature. Stripe events arrive out of order, dedupe carefully.",
         ["billing", "reconciliation", "lesson"],
         abstracts_to=[]),
]

# ---------------------------------------------------------------------------
# INGEST service
# ---------------------------------------------------------------------------

INGEST_SEEDS: list[Seed] = [
    # 27 user_said
    Seed("must handle 10k eps",
         "User requirement: ingest must handle 10k events/sec sustained",
         "user_said",
         "Top-3 enterprise customers send ~10k events/sec at peak. Need to handle 2x that for headroom.",
         "Stated by the head of customer success after losing a renewal over ingest backpressure.",
         ["ingest", "user_said", "perf"],
         abstracts_to=[]),
    # 28
    Seed("Kafka backbone",
         "Decision: Kafka as the ingest backbone",
         "decision",
         "All ingest events land in Kafka (3-broker cluster, RF=3, 30-day retention). Downstream consumers fan out from there.",
         "Considered Kinesis (vendor lock-in) and NATS (less proven at our scale). Kafka chosen for ecosystem.",
         ["ingest", "kafka"],
         abstracts_to=[]),
    # 29
    Seed("cursor pagination",
         "Decision: cursor-based pagination on /events read API",
         "decision",
         "Read API uses opaque cursors based on (timestamp, event_id). No offset-based paging.",
         "Originally used offset; switched after the offset-perf incident.",
         ["ingest", "api", "pagination"],
         abstracts_to=[]),
    # 30
    Seed("offset perf incident",
         "Incident: /events offset-paging killed a tenant's query latency",
         "incident",
         "Customer reported 30s+ load times paging past the 500k-event mark. Postgres OFFSET 500000 was the culprit.",
         "Hotfix: capped page count at 50. Permanent fix: cursor-based pagination (note 29).",
         ["ingest", "incident", "perf"],
         abstracts_to=[]),
    # 31
    Seed("offset original",
         "Decision (superseded): offset-based pagination on /events",
         "decision",
         "Original 2024 design used limit+offset. Worked fine until customers crossed ~100k events.",
         "Superseded by note 29 after the offset-perf incident.",
         ["ingest", "pagination", "legacy"],
         abstracts_to=[]),
    # 32
    Seed("schema evolution",
         "Decision: JSON schema with additive evolution",
         "decision",
         "Event schemas are JSON; new fields are additive, never required. Removals require a 90-day deprecation window.",
         "Rejected protobuf for ergonomic reasons (customers want to send JSON from anywhere). Accepting the parsing cost.",
         ["ingest", "schema", "compat"],
         abstracts_to=[]),
    # 33  EXPERIMENT
    Seed("batch size sweep",
         "Experiment: producer batch-size sweep for throughput",
         "experiment",
         "Tested batches of 1, 10, 100, 1000, 10000 events. 1000 was the knee — diminishing returns above; tail latency grows.",
         "Currently using 1000-event batches with linger.ms=20. Reaches 12k eps on a single producer.",
         ["ingest", "kafka", "experiment", "perf"],
         abstracts_to=[]),
    # 34
    Seed("dedup on ingest",
         "Decision: dedupe events on (tenant_id, event_id) at ingest",
         "decision",
         "Events with duplicate (tenant_id, event_id) within the last 24h are dropped silently.",
         "Customer SDKs sometimes retry without proper idempotency; we absorb the duplicates rather than push the problem upstream.",
         ["ingest", "dedup"],
         abstracts_to=[]),
    # 35  LESSON
    Seed("backpressure to producer",
         "Lesson: surface backpressure to the producer SDK",
         "lesson",
         "Silently dropping events under pressure cost us a customer. Now the SDK gets a 429 with Retry-After and buffers.",
         "Lost a contract in early 2025 because we 5xx'd silently when our pipeline was behind. Now we explicitly signal back.",
         ["ingest", "backpressure", "lesson"],
         abstracts_to=[]),
    # 36
    Seed("retention 30d",
         "Decision: 30-day raw retention in Kafka",
         "decision",
         "Raw events kept for 30 days in Kafka; aggregated tier kept for 13 months in Postgres.",
         "Balances cost vs replay-for-debugging window.",
         ["ingest", "retention"],
         abstracts_to=[]),
    # 37  PRINCIPLE
    Seed("backpressure is contract",
         "Principle: backpressure is a contract, not an error",
         "principle",
         "Systems with finite capacity must communicate capacity to upstream callers, not silently drop or 5xx.",
         "Generalized from the silent-drop incident; applies to ingest, billing webhooks, email sends.",
         ["ingest", "principle", "backpressure"],
         abstracts_to=[35]),
    # 38
    Seed("schema breakage",
         "Incident: schema-strict consumer broke on a new optional field",
         "incident",
         "An internal analytics consumer used a strict schema validator that failed on additive fields, blocking ingest for 4h.",
         "Fix: relaxed-mode validators downstream; CI now exercises both strict and relaxed paths.",
         ["ingest", "incident", "schema"],
         abstracts_to=[]),
    # 39
    Seed("partition by tenant",
         "Decision: partition Kafka topics by tenant_id",
         "decision",
         "topic 'events' partitioned by hash(tenant_id) mod 64. Per-tenant ordering preserved.",
         "Considered partition by event_type; tenant_id won because per-tenant scaling and isolation matters more.",
         ["ingest", "kafka", "partitioning"],
         abstracts_to=[]),
    # 40
    Seed("noisy neighbor",
         "Incident: one big tenant pinned a partition at 100% CPU",
         "incident",
         "A whale customer kept partition 7 saturated for 6 hours; smaller tenants on that partition saw elevated latency.",
         "Mitigation: dynamic rebalancing for top-N tenants onto dedicated partitions. Long-term: per-tenant quotas at the producer.",
         ["ingest", "incident", "isolation"],
         abstracts_to=[]),
]

# ---------------------------------------------------------------------------
# CROSS-SERVICE / TEAM
# ---------------------------------------------------------------------------

TEAM_SEEDS: list[Seed] = [
    # 41 user_said
    Seed("ship monthly",
         "Team policy: ship a customer-visible improvement monthly",
         "user_said",
         "Founder: 'visible progress every calendar month or the company dies'.",
         "Drives the release cadence. Affects what gets prioritized; refactors compete with features.",
         ["team", "user_said"],
         abstracts_to=[]),
    # 42 PRINCIPLE
    Seed("rollback always",
         "Principle: every deploy must be rollback-safe",
         "principle",
         "Every schema migration must be reversible in <5 minutes. Feature flags default off.",
         "Hard rule. We accept slightly slower rollouts in exchange for the ability to undo.",
         ["deploy", "principle"],
         abstracts_to=[]),
    # 43
    Seed("staging is prod-shaped",
         "Decision: staging environment mirrors prod cardinality",
         "decision",
         "Staging gets a daily anonymized subset of prod data, ~5% volume but full diversity of tenants.",
         "Synthetic staging missed too many bugs that surfaced under realistic data shapes.",
         ["deploy", "staging"],
         abstracts_to=[]),
    # 44
    Seed("monorepo",
         "Decision: monorepo for all services",
         "decision",
         "All three services (auth, billing, ingest) plus the web frontend live in one git repo.",
         "Atomic cross-service refactors > separate-repo isolation, for our size.",
         ["team", "monorepo"],
         abstracts_to=[]),
    # 45  LESSON
    Seed("oncall rotation small",
         "Lesson: a 4-person oncall rotation is the floor",
         "lesson",
         "With fewer than 4 people, vacation + sickness made oncall coverage impossible. Now we won't put a service on oncall until we have 4 trained engineers.",
         "Source: Q3 2025 when the billing team had 3 people and one took medical leave.",
         ["team", "oncall", "lesson"],
         abstracts_to=[]),
    # 46
    Seed("postmortems blameless",
         "Decision: blameless postmortems within 5 days of incident",
         "decision",
         "Every Sev-2+ gets a written postmortem within 5 business days. No individual blame; focus on systems and contributing factors.",
         "Aligned with industry best practice; ensures we capture lessons before context fades.",
         ["team", "incident", "process"],
         abstracts_to=[]),
    # 47
    Seed("observability stack",
         "Decision: OpenTelemetry + Grafana for observability",
         "decision",
         "All services emit OTLP traces and metrics; Grafana dashboards and Loki for logs.",
         "Vendor-neutral; we'd previously locked into a SaaS APM that became unaffordable.",
         ["observability"],
         abstracts_to=[]),
    # 48
    Seed("saas APM retired",
         "Decision (superseded): use Datadog for everything",
         "decision",
         "Original 2024 choice. Hit ~$15k/mo at our scale; replaced by OTel + Grafana (note 47).",
         "Datadog was great UX, untenable cost. Migration took 3 sprints.",
         ["observability", "legacy"],
         abstracts_to=[]),
    # 49  LESSON
    Seed("vendor cost surprises",
         "Lesson: SaaS bills scale faster than headcount",
         "lesson",
         "Every SaaS we adopted at <$100/mo passed $3k/mo within 18 months. Two passed $15k/mo.",
         "Standing rule: before adopting any SaaS, project 24-month cost at 5x current volume.",
         ["team", "cost", "lesson"],
         abstracts_to=[48]),
    # 50  PRINCIPLE (overarching)
    Seed("buy small, build big",
         "Principle: buy commodity, build differentiators",
         "principle",
         "Anything that's commodity (auth-as-a-service for OAuth providers, email delivery, tax) can be bought. The product itself is built in-house.",
         "Sits above the no-SaaS-for-billing constraint; tax is OK to buy because it's pure commodity. Billing isn't.",
         ["team", "principle", "build-vs-buy"],
         abstracts_to=[13, 20, 49]),
    # 51
    Seed("hiring senior bias",
         "Decision: bias toward senior hires in 2025",
         "decision",
         "Stopped hiring juniors in mid-2025. Team too small to mentor effectively.",
         "Will revisit when we hit 12+ engineers and have a clear mentorship structure.",
         ["team", "hiring"],
         abstracts_to=[]),
    # 52
    Seed("daily-standup tried",
         "Experiment: daily standup, 2-month trial",
         "experiment",
         "Tried 15-minute daily standups in Q1 2025. Discontinued after 2 months; weekly works better at our size.",
         "Standups felt performative below ~8 engineers; people forgot updates between standups anyway.",
         ["team", "process", "experiment"],
         abstracts_to=[]),
    # 53 LESSON
    Seed("docs after, not during",
         "Lesson: docs written during build are wrong",
         "lesson",
         "Pre-write docs were inaccurate ~70% of the time by ship date. Post-ship docs were accurate.",
         "Now we ship + spend the first sprint after ship cleaning up docs.",
         ["team", "docs", "lesson"],
         abstracts_to=[]),
    # 54
    Seed("api versioning",
         "Decision: URL-based API versioning (/v1, /v2)",
         "decision",
         "Public APIs use /v1/ prefix; major-version-only versioning. No header-based negotiation.",
         "Considered Accept-header but client SDKs in customer hands made URL paths simpler to communicate.",
         ["api", "versioning"],
         abstracts_to=[]),
    # 55
    Seed("breaking change policy",
         "Decision: 12-month deprecation window for breaking API changes",
         "decision",
         "Once announced, a deprecated endpoint is supported for 12 months. Customers get monthly nag emails in the last quarter.",
         "Balances customer pain vs engineering carrying-cost of duplicate code paths.",
         ["api", "policy"],
         abstracts_to=[]),
]

ALL_SEEDS = AUTH_SEEDS + BILLING_SEEDS + INGEST_SEEDS + TEAM_SEEDS


# ---------------------------------------------------------------------------
# Wire up some cross-section related edges + supersedes
# ---------------------------------------------------------------------------

# (source_idx, target_idx, type)
EXTRA_EDGES: list[tuple[int, int, str]] = [
    # supersedes
    (1, 9, "supersedes"),     # Argon2id supersedes bcrypt
    (22, 23, "supersedes"),   # dunning ladder supersedes brute retry
    (29, 31, "supersedes"),   # cursor pagination supersedes offset
    (47, 48, "supersedes"),   # OTel supersedes Datadog
    # cross-service related
    (17, 34, "related"),      # idempotency principle ↔ ingest dedup
    (37, 35, "related"),      # backpressure principle ↔ backpressure lesson (same area)
    (8, 11, "related"),       # defense-in-depth ↔ forced-logout race
    (42, 30, "related"),      # rollback-safe ↔ offset-perf incident
    (50, 14, "related"),      # buy-small-build-big ↔ Postgres billing
    (12, 11, "related"),      # flaky-tests-reveal-bugs ↔ forced-logout race
    (26, 16, "related"),      # reconciliation lesson ↔ double-charge
    (17, 16, "abstracts"),    # idempotency principle abstracts the double-charge incident
    (8, 6, "abstracts"),      # defense-in-depth abstracts the token-leak incident
    (37, 40, "abstracts"),    # backpressure principle abstracts noisy-neighbor incident
    (50, 47, "abstracts"),    # buy/build principle abstracts OTel decision
    (45, 11, "related"),      # oncall floor lesson ↔ forced-logout race
]


def build(store_root: Path, *, n_extra_filler: int = 100) -> dict:
    """Build the synthetic graph at store_root.

    Returns a summary dict.
    """
    from memory_graph.embed import LocalEmbedder
    from memory_graph.primitives import Store
    from memory_graph.storage import Edge

    store = Store(store_root, embedder=LocalEmbedder())
    try:
        # Pass 1: write all seeded notes, recording the id assignment.
        ids: list[str] = []
        for i, s in enumerate(ALL_SEEDS):
            r = store.capture(
                title=s.title,
                short_label=s.short_label,
                summary=s.summary,
                body=s.body,
                kind=s.kind,
                tags=s.tags,
            )
            ids.append(r["id"])

        # Pass 2: draw the seed-list's abstracts edges (parent → child).
        for parent_idx, s in enumerate(ALL_SEEDS):
            for child_idx in s.abstracts_to:
                store.link(ids[parent_idx], ids[child_idx], "abstracts")

        # Pass 3: explicit cross-cutting edges.
        for src_idx, dst_idx, etype in EXTRA_EDGES:
            if etype == "supersedes":
                store.supersede(
                    old_id=ids[dst_idx],
                    new_id=ids[src_idx],
                    reason="newer choice / mitigation",
                )
            else:
                store.link(ids[src_idx], ids[dst_idx], etype)

        # Pass 4: filler notes — short bullet-style observations to add bulk
        # so retrieval has real noise to filter through. Tagged with a
        # generic 'log' tag so the eval can ignore them.
        rng = random.Random(42)
        verbs = ["Investigated", "Profiled", "Audited", "Reviewed", "Rolled out",
                 "Patched", "Documented", "Tuned", "Benchmarked", "Rate-limited",
                 "Migrated", "Renamed", "Refactored", "Hardened"]
        nouns = ["the rate limiter", "the JSON parser", "the migration script",
                 "the worker pool", "the connection pool", "the retry budget",
                 "the metrics exporter", "the dashboard query", "the cron job",
                 "the cache layer", "the backup job", "the seed data",
                 "the search index", "the email queue", "the SDK client"]
        for i in range(n_extra_filler):
            v = rng.choice(verbs)
            n = rng.choice(nouns)
            short = f"{v.lower()[:6]} {n.split()[-1]}"
            store.capture(
                title=f"{v} {n}",
                short_label=short,
                summary=f"{v} {n} on {rng.choice(['mon','tue','wed','thu','fri'])}.",
                body=f"{v} {n}. Routine operational note. No surprises.",
                kind="observation",
                tags=["log"],
            )

        # Snapshot.
        return {
            "store_root": str(store_root),
            "named_ids": dict(zip(_name_keys(), ids)),
            "named_count": len(ALL_SEEDS),
            "filler_count": n_extra_filler,
            "total_nodes": len(ALL_SEEDS) + n_extra_filler,
        }
    finally:
        store.close()


def _name_keys() -> list[str]:
    """Stable keys for the named notes — uses short_label, fallback to title."""
    return [s.short_label for s in ALL_SEEDS]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("store_root", help="path to .memory-graph/ dir (will be created)")
    p.add_argument("--filler", type=int, default=100,
                   help="number of generic filler observation notes")
    args = p.parse_args(argv)

    root = Path(args.store_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "notes").mkdir(exist_ok=True)
    (root / "_operator").mkdir(exist_ok=True)
    (root / "_pending").mkdir(exist_ok=True)

    summary = build(root, n_extra_filler=args.filler)
    print("Built synthetic graph:")
    print(f"  store_root:    {summary['store_root']}")
    print(f"  total nodes:   {summary['total_nodes']}")
    print(f"  named notes:   {summary['named_count']} (semantically meaningful)")
    print(f"  filler:        {summary['filler_count']} (operational noise)")

    # Persist the named-id mapping so the retrieval tasks can reference it.
    import json
    map_path = root.parent / "named_ids.json"
    map_path.write_text(json.dumps(summary["named_ids"], indent=2))
    print(f"  id map:        {map_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
