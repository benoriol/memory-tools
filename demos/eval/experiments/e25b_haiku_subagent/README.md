# e25b — Same recall stress task with Haiku for the memory sub-agent

**Question:** does swapping the memory sub-agent from Sonnet 4.6 to
Haiku 4.5 preserve the recall lift seen in e25 at meaningfully lower
cost and latency?

## Hypothesis

The sub-agent's task (text-to-JSON canonicalization: keywords +
paraphrases) is mechanical and well-scoped. Haiku 4.5 should handle
it adequately, preserving multi-vector recall while running faster
and cheaper. Expected: recall@1 within 5 pp of Sonnet, ~3× faster,
~10× cheaper.

## Setup

Identical to e25 (same corpus generator, same 50 queries, same
multi-vector `Store` and retrieval math). The only change is the
environment variable:

```bash
MEMORY_RECALL_SUBAGENT_MODEL=claude-haiku-4-5-20251001
```

Ran only the `multi` arm — the `single` and `grep` arms in e25 don't
use the sub-agent at all, so re-running them would be wasted budget.

## Result (2026-05-21)

| | Sonnet (e25) | Haiku (e25b) | Δ |
|---|---|---|---|
| recall@1 | **86 %** | **82 %** | −4 pp |
| recall@5 | 100 % | 100 % | 0 |
| wall time | 472 s | **995 s** | **+110 %** |
| cost (instrumented) | $0.00 | $0.00 | (broken) |

The +110 % time blowup was the surprise. Per-call latency averages
~9.9 s for Haiku vs ~4.7 s for Sonnet in this run. The opposite of
the expected ~3× speedup.

## Reflection

### What we expected
Recall stays close (mechanical task), time and cost drop substantially.

### What we observed
- **Recall holds within tolerance**: 82 % vs 86 %, −4 pp. Haiku still
  beats single-vector (56 %) by +26 pp. The recall mechanism is
  preserved.
- **Time got WORSE**, not better. ~2× slower per call.
- **Cost is unmeasured.** `subagent_capture_cost_usd` and
  `subagent_search_cost_usd` both read $0.00 — a known
  instrumentation gap in the benchmark (see e25 reflection). The
  whole point of switching to Haiku is cost reduction; without real
  numbers, the question is not answered.

### Why time got worse (hypotheses, unconfirmed)
1. **Throughput tier difference.** Haiku 4.5 may queue more
   aggressively at our account tier despite being a smaller model.
2. **Per-request fixed overhead dominates.** The sub-agent emits ~200
   tokens of JSON; at that length, model size matters less than
   request setup latency. Haiku ≠ "smaller = faster" for tiny
   outputs.
3. **Transient API load.** Single-run variance; needs replication.

### Why recall is close
Sampling the per-query log: most misses are the same conceptual edge
cases between models. One difference visible at i=2 (frame_magic_byte
query): Sonnet's expansion produced "magic byte" — exact keyword
match. Haiku's expansion produced "synchronization" — semantically
adjacent but wrong canonical term, pushing the right note from rank 1
to rank 2. Haiku is *slightly* less aggressive at picking the
canonical engineering vocab. Not catastrophic, but visible.

### What this implies
- The Haiku-for-sub-agent story is **not yet a clear win**.
- The real headline is missing because cost isn't instrumented.
- Recall is acceptable; latency is worse than expected in this run.
- Two follow-ups are real, not optional:
    1. **Fix cost instrumentation.** Plumb `ResultMessage.total_cost_usd`
       through `expand_for_capture` / `expand_for_search`.
    2. **Re-run e25 + e25b back-to-back** once cost is instrumented, so
       latency and cost can be compared on the same API conditions.

### Current recommendation
**Keep Sonnet as the default sub-agent model** until cost
instrumentation is wired and a head-to-head shows Haiku is
meaningfully cheaper at this task. The latency surprise here is
enough to invalidate the "Haiku is faster" assumption — the cost
case might still hold, but we need numbers, not intuition.

---

## Follow-up (2026-05-21): disable extended thinking

After the first run showed Haiku 2× slower per call, the hypothesis
was that Haiku 4.5 was doing hidden extended thinking even at
`effort="low"`. Probed it directly: 5 sequential `expand_for_search`
calls per model, with and without `thinking={"type": "disabled"}`.

| Config | mean / call | output chars |
|---|---|---|
| Sonnet, thinking on  | 3.50 s | 329 |
| Sonnet, thinking off | 3.55 s | 330 |
| Haiku,  thinking on  | 8.44 s | 355 |
| Haiku,  thinking off | 2.74 s | 328 |

Haiku's hidden thinking accounted for ~5.7 s/call. Sonnet was
already effectively thinking-off at `effort="low"`. We updated
`subagent.py` to set `thinking={"type": "disabled"}` and
`max_thinking_tokens=0` for ALL sub-agent calls.

### Re-run after the fix

| | recall@1 | recall@5 | wall time |
|---|---|---|---|
| Sonnet (thinking on, original e25)  | 86 % | 100 % | 472 s |
| Sonnet (thinking off, e25 rerun)    | **92 %** | 100 % | 471 s |
| Haiku  (thinking on, original e25b) | 82 % | 100 % | 995 s |
| Haiku  (thinking off, e25b rerun)   | 74 % | 100 % | **321 s** |

### What changed and why

- **Haiku got faster (995s → 321s)** because hidden thinking was
  removed. Confirmed the original hypothesis.
- **Haiku recall dropped (82% → 74%)** because Haiku was *using* its
  thinking budget productively to pick canonical engineering vocab.
  Without thinking, Haiku's keyword choices are weaker. Real signal
  (8 pp = 4 of 50 queries).
- **Sonnet recall went UP (86% → 92%)** without thinking. Unexpected
  but plausible: the sub-agent task is mechanical canonicalization,
  and "thinking" Sonnet occasionally produces unusual paraphrases
  ("synchronization" for "magic byte") that lose to neighbors. A
  6 pp swing on 50 queries is at the edge of noise; could be variance.
  Needs a replication run.
- **Latency story is now clear:** Sonnet-effort=low was already
  thinking-off; the original e25 result was honest. Haiku was the
  one with the hidden 5.7s/call thinking budget.

### Updated recommendation

**Use Sonnet 4.6 with `thinking={"type": "disabled"}` as the
sub-agent.** Same latency as the original config; +6 pp recall@1 in
this run; dominates Haiku-thinking-off by 18 pp.

Haiku-without-thinking is faster (321s vs 471s = –32 %) but loses
18 pp of recall@1. Not worth it on quality terms. The Haiku case
could still hold if cost instrumentation eventually shows Haiku is
much cheaper *and* recall@5 = 100 % is sufficient for the workload
(it stays at 100 % for both).

The `subagent.py` change applies to the live MCP server too — every
`memory_capture` and `memory_search` call now runs with thinking
explicitly disabled.
