# e25 — Multi-vector vs single-vector vs grep on cross-vocabulary recall

**Question:** Q2 — does multi-vector recall (sub-agent generated views,
max-pooled cosine) beat single-vector retrieval (one embedding per note
body) and beat keyword grep, when queries are *phrased orthogonally*
from the note bodies?

## Hypothesis

When the query vocabulary is intentionally different from the body's,
single-vector cosine has a hard time bridging the lexical gap, and
grep is hopeless. The multi-vector arm pays a sub-agent at capture
time to enumerate paraphrases and keywords; this should buy a real
recall lift on the recall stress task.

Specifically, **multi-vector**
- recall@1 ≥ single-vector recall@1 + 0.10, OR
- recall@5 ≥ single-vector recall@5 + 0.05.

## Design

- **Corpus:** 50 short technical notes generated in-code. Each note's
  body is a single declarative sentence using domain-specific
  vocabulary (e.g. "The OutboundBreaker class wraps every external HTTP
  call and opens after five consecutive failures.").
- **Queries:** 50 paired queries, one per note. Each query is
  phrased orthogonally to the body — different vocabulary, same
  referent (e.g. "Which component shields us from cascading failures
  when a downstream service is misbehaving?"). Truth is held in the
  script, not on disk.

Three arms:

### grep
- An agent given the `notes/` directory and Bash/Read/Grep tools.
- For each query the agent searches markdown and answers with the
  matching filename.
- No embeddings used.

### single
- Each note's body is embedded once with FastEmbed MiniLM-L6-v2.
- At query time the verbatim query is embedded; top-k by cosine.
- No sub-agent. Deterministic.

### multi (this design)
- Capture: `expand_for_capture` produces summary + 3-5 keywords +
  2-3 paraphrases. All views embedded.
- Search: `expand_for_search` produces keywords + paraphrases plus
  the verbatim query. All views embedded, cosine vs every note-view,
  max-pool to a per-note score.

## Metrics (per arm)

- recall@1
- recall@5
- total cost (USD): main agent + sub-agent
- For `multi`: sub-agent capture cost and sub-agent search cost
  separately
- latency: total wall-clock seconds

## Pass criterion (pre-declared)

`multi` recall@1 ≥ `single` recall@1 + 0.10
**OR**
`multi` recall@5 ≥ `single` recall@5 + 0.05.

(Either is sufficient. The first is a strict-precision test; the
second a moderate-coverage test.)

## How to run

```bash
cd demos/eval/experiments/e25_multivec_vs_singlevec
python e25.py 2>&1 | tee run.log
# or:
python e25.py --dry-run    # smoke-check, no sub-agent calls
```

Expected runtime: ~5-10 minutes for a full run (50 captures × 1 sub-
agent call each, plus 50 query expansions).

## Result (2026-05-21)

| | recall@1 | recall@5 | time | cost |
|---|---|---|---|---|
| single-vector | **56%** | 98% | 2.0s | $0 (no LLM) |
| grep (LLM-driven) | 100% | 100% | 474.1s | $1.16 |
| multi-vector | **86%** | 100% | 471.9s | (cost instrumentation missing) |

**Verdict: PASS.** Multi-vector recall@1 vs single-vector: **+30 pp**
(≥10 pp required, easily clears the threshold).

## Reflection

### What we expected
On a recall-stress task (queries phrased orthogonally to note bodies),
single-vector retrieval would frequently miss at rank 1 because the
embedder can't bridge the lexical gap with one fixed projection.
Multi-vector with sub-agent-generated views should lift recall@1 by at
least 10 percentage points.

### What we observed
- **Single-vector's failure mode is precisely "right answer hovering
  near the top but not at it"**: recall@5 is 98% but recall@1 is only
  56%. Reading the per-query log, the right note routinely ranks 2nd
  or 3rd, beaten by a semantically-adjacent neighbor.
- **Multi-vector fixes this**. The same 50 queries hit at rank 1 in
  86% of cases. The mechanism is the keyword and paraphrase views at
  capture time, plus the keyword/paraphrase expansion at query time.
  When both sides emit something like "circuit breaker", they cosine
  to 1.0 exactly, lifting that note above its semantic neighbors.
- **Grep with an LLM agent is a ceiling, not a baseline**. The grep
  arm scored 100% because the agent iteratively refined search
  patterns using its own reasoning — the intelligence is in the
  agent, not the retrieval mechanism. Useful as a "what if the agent
  has unlimited budget" reference; less useful for comparing
  retrieval-only designs.
- **Wall time** is dominated by sub-agent LLM calls in the multi-vector
  arm (50 captures × ~5s + 50 expansions × ~5s ≈ 8 min). The cosine
  math itself is microseconds. So multi-vector's time cost is paid as
  LLM tokens, not retrieval compute — a useful framing for
  optimization.

### Why this matters
The user's intuition was right: a flat list with single-vector
retrieval has a real ceiling on recall@1 when queries don't share
vocabulary with the corpus. Multi-vector retrieval — capture-time
view enumeration + retrieval-time query expansion — closes that gap
substantially.

The mechanism isn't about embedding capacity per se; it's about
**covering multiple semantic surfaces** of each memory with separate
clean vectors, and then asking the query in multiple forms so at
least one matches one of them. Each pair of (one query view, one
note view) is one chance to hit; max-pooling takes the best chance.
With ~7 query views and ~9 note views per query×note pair, that's 63
chances per pair, vs 1 for single-vector. That's why the gap is so
large.

### Open issues
1. **Sub-agent cost instrumentation is missing** for the multi arm.
   `subagent_capture_cost_usd` and `subagent_search_cost_usd` both
   read $0.00, but the actual cost is non-zero (likely ~$0.50–$1.00).
   Plumb `ResultMessage.total_cost_usd` through `expand_for_capture`
   and `expand_for_search` so the benchmark gets real numbers.
2. **Grep arm is mis-framed** as a baseline; it's a ceiling. Future
   benchmarks should keep it for context but not treat it as the
   thing-to-beat for retrieval-mechanism comparisons.
3. **Latency is dominated by sub-agent calls**. The natural follow-up
   is e25b: same task with **Haiku** for the sub-agent, measuring
   recall and cost. If Haiku preserves the recall gap at ~10× lower
   sub-agent cost, that's the production recommendation.

### Implications for the larger plan
- **Q2 partial answer**: storage shape matters less than retrieval
  surface area. Multi-vector beats single-vector by a wide margin
  even though the *storage* is structurally the same flat-list.
- **The graph variants (e30, e40)** still need their day, but the
  bar they have to clear is now higher: any structural retrieval
  scheme has to beat multi-vector flat retrieval, not single-vector.
- **The next bet** is e25b (cheaper sub-agent) before any more
  structural variants.
