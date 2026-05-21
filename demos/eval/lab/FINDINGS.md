# Lab notebook: when does memory matter?

## TL;DR

Memory helps in **cross-session work**, not single-session work.

- **B7 (capability)**: when source is deleted between sessions, no_memory
  scores 0/30 and with_memory scores 30/30. But this is the degenerate
  case — memory is literally the only physical channel.
- **B11 (cost/speed)**: when source remains on disk but the phase-2 agent
  starts cold (no in-context history of phase 1's grep), memory still
  wins clearly — phase-2 cost is **2.7× lower** and time **1.8× lower**
  at identical accuracy (30/30). This is the realistic case.
- **Single-session (B1, B8, B9, B9v2, B10)**: memory is net overhead.
  The agent prefers grep + Read; when forced to use memory tools, the
  capture-then-retrieve cycle exceeds the savings.

## All experiments

| ID  | Task                                | no_memory          | with_memory     | Memory's effect |
|-----|-------------------------------------|--------------------|-----------------|------------------|
| B1  | Cross-module audit (L1..L10)        | 1.00 every level   | 1.00 (L10)      | +18% cost, no gain |
| B2  | Black-box piecewise oracle          | 1.00 / $0.23       | not run         | n/a |
| B3  | Bio corpus, multi-attribute join    | 1.00 / $0.35       | not run         | n/a |
| B4  | Heterogeneous log anomalies         | 1.00 / $0.05       | not run         | n/a |
| B5  | Implicit contradictions             | 1.00 / $0.15       | not run         | n/a |
| B6  | Buried fact in 80KB narrative       | 1.00 / $0.14       | not run         | n/a |
| **B7**  | **Cross-session arch recall** | **0/30, $0.10**  | **30/30, $0.31** | **+capability** |
| B8  | Semantic Q&A, 30 fictional docs     | 30/30 / $0.076     | 30/30 / $0.099  | -30% (memory wastes) |
| B9  | Semantic Q&A, 800 docs, 1.16MB      | 20/20 / $0.30      | 20/20 / $0.11   | apparent +63%, but **0 notes written** — noise |
| B9v2| Same + explicit memory instruction  | 20/20 / $0.30      | 20/20 / $0.15   | apparent +51%, **still 0 notes** — agent ignored memory |
| B10 | 3000-doc paraphrased queries, 2.1MB | 20/20 / $0.33      | 20/20 / $0.35   | -5%, **20 notes used** but still slower (181s vs 133s) |
| **B11** | **Cross-session recall, files KEPT** | **30/30 / $0.38, p2=$0.155** | **30/30 / $0.23, p2=$0.056** | **+40% total cost saved, p2 2.7× cheaper** |

## What the failed single-session attempts taught us

**B9 and B9v2 cost gaps were not memory's doing.** The with_memory agent
captured zero notes in both runs, even with explicit instructions to use
memory_capture_batch. The cost difference between arms (~$0.15) was just
variance in how Sonnet chose to grep the filesystem. We were measuring
prompt-phrasing effects, not memory.

**B10 finally got the agent to use memory** (20 notes) by using a more
emphatic "REQUIRED: actually use memory tools" prompt. But the result
was *worse* than no_memory: +36% time, +5% cost, identical accuracy.
The capture-then-retrieve overhead didn't pay back, because at 2.1MB the
no_memory agent could just grep the filesystem and read the matched docs
directly. Memory didn't have a unique advantage to offer.

**Implication for single-session work:**
For corpora the agent can navigate with grep/glob and that fit in (or
near) the 1M context window, Bash + filesystem is *not just adequate but
preferred*. The agent will refuse to use memory tools even when
instructed if grep is simpler. And when forced, the overhead exceeds the
savings.

## The realistic cross-session case (B11)

B11 is the version of B7 that doesn't cheat: same 30 architectural facts,
but in phase 2 the source files are STILL ON DISK. Phase-2 questions are
paraphrased so grep on the question text returns nothing useful — the
no_memory agent has to actually read modules to find conceptual matches.
Each phase is a fresh `query()` call, so there's no in-context carryover.

|                         | no_memory  | with_memory       |
|-------------------------|------------|-------------------|
| Phase 1 cost / time     | $0.22 / 72s | $0.17 / 93s      |
| Phase 1 notes captured  | n/a        | 30                |
| **Phase 2 cost / time** | **$0.15 / 37s** | **$0.06 / 21s** |
| Phase 2 accuracy        | 30/30      | 30/30             |
| **Total cost**          | **$0.38**  | **$0.23 (-40%)**  |

Phase-2 alone, with_memory is **2.7× cheaper and 1.8× faster** at
identical accuracy. The 30 notes captured in phase 1 are retrieved
semantically and the agent never re-reads source.

Phase 1 is also cheaper with memory ($0.17 vs $0.22) — `memory_capture_batch`
is more token-efficient than the verbose text recap no_memory produces.
Phase 1 is slightly *slower* wall-clock (93s vs 72s) due to the
capture-batch round trips, but the cost flips.

This is the realistic working pattern: a developer comes back tomorrow,
the code is still there, but their grep history isn't. Memory bridges
that gap profitably.

## The degenerate cross-session case (B7)

| | no_memory | with_memory |
|---|---|---|
| Score | **0/30** | **30/30** |
| Cost | $0.10 | $0.31 |
| Time | 43s | 131s |

Source files deleted between phases. no_memory has nothing to consult and
honestly declines all 30 questions. with_memory captured each fact during
phase 1 and recalled them perfectly.

This is "degenerate" because deletion makes memory the only physical
channel — of course it wins. The honest version is B11 above, where the
no_memory agent could in principle re-derive everything from the files
that are still on disk. B11 shows memory still wins on cost in that
realistic setup; B7 only proves what happens when re-derivation is
impossible.

## What this implies for the tool's positioning

The honest framing:

1. **Cross-session is the load-bearing use case.** When a developer comes
   back tomorrow, when one teammate hands off to another, when a long
   project spans many `claude` invocations — that's where memory_graph
   pays back.

2. **Within a single session, memory tools are net overhead** for tasks
   where the corpus fits in context or can be navigated with grep. The
   1M Sonnet context window is large enough that single-session work
   rarely strains it, and Bash + filesystem is already a perfect scratch
   space.

3. **For genuinely massive corpora (>>4MB)** that don't fit in any single
   context, memory's structured retrieval might still win, but we didn't
   find a clean demonstration — even at 2MB across 3000 docs, the agent
   preferred filesystem grep to memory_capture_batch. Forcing memory use
   via prompt didn't help; it hurt.

## Why single-session memory wins are hard to find

Every single-session experiment reduced to the same agent strategy:

  1. Glob the directory.
  2. Grep for relevant terms (sometimes a careful one-pass Read).
  3. Answer.

That pipeline does not benefit from memory tools and explicitly competes
with them on cost. To find single-session memory wins, we'd need a task
where:

  - grep is fundamentally inadequate (truly semantic queries with zero
    keyword overlap), AND
  - the corpus is too large to read entirely (well beyond 1M tokens), AND
  - the queries are numerous enough that capture-once overhead amortizes.

We tried each of these in isolation; none produced a single-session win.
The combination (corpus >10MB + zero-overlap queries + 50+ questions)
might tip the balance, but it's an unrealistic benchmark.

The real lever isn't query semantics or corpus size — it's the **session
boundary**. Even on a small corpus (30 modules), B11 shows that once
the in-context navigation history is gone, re-deriving findings costs
2-3× more than retrieving cached ones. Memory's value is preserving
cognitive work *across* the session boundary, not replacing grep
*within* a session.

## Recommendation

The protocol section in `templates/claude_protocol.md` should be honest
about this:

- "Use memory at the **start and end** of each session — capture key
  decisions before you stop, retrieve prior work before you continue."
- "Don't bother with memory for one-shot audits or single-prompt
  investigations — the agent's filesystem scratch is faster."

This matches the existing recommendation for `memory_remember` /
`memory_retrieve` / `memory_compact`, which are positioned as
session-boundary tools, not in-session helpers.
