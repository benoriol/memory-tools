# Research questions

The lab work exists to answer four questions. Status is current as of B11.

## Q1. Does memory help at all?

**Answer: yes — across the session boundary.**

Within a single session, the agent's Bash + 1M context already covers
the work; memory tools are net overhead (B1, B8, B9, B10).

Across sessions, when the in-context navigation history is gone, even
keeping the source files on disk, memory's persisted notes beat
re-investigation by ~2.7× on phase-2 cost at identical accuracy (B11).

So the open questions below are not "does it help" — they're "what is
the right shape of the memory store?"

---

## Q2. What is the best way to STORE memory?

Three candidates, with their open issues:

### (a) Single file
- **Pro:** trivial to write, trivial to read, all context loaded at once.
- **Con:** every retrieval pulls the entire file into context. Caching
  softens this but the file grows without bound; eventually the
  whole-file load swamps the relevant-fact-only load.
- **Status:** this is essentially what the no_memory arm in B11 did
  (`ARCHITECTURE_FACTS.md`). Memory beat it 2.7×.

### (b) Multiple isolated files
- **Pro:** granular retrieval — only load what's relevant.
- **Open:**
  - How to index them (filename conventions? embedding index? both?).
  - How to identify duplicates so the store doesn't grow with redundancy.
  - How to search them efficiently (keyword? semantic? hybrid?).
  - How to surface relationships between facts when they're related.
- **Status:** untested directly. This is currently the strongest
  candidate by reasoning, since it's a special case of (c) with no edges.

### (c) Graph (multi-file with explicit relations)
- **Pro:** captures structure beyond flat lookup — "this fact depends
  on that one", "these two facts contradict", "this is an abstraction
  of those details".
- **Con:** added machinery, added cost at capture time, added cost at
  retrieval time. If queries don't need the structure, it's overhead.
- **Status:** the current `memory_graph` tool. The graph machinery was
  idle in B11 — every question was an independent point lookup, so
  `memory_neighbors` did no work. We have not found a benchmark yet
  where the graph itself moves the result.

---

## Q3. Does a graph help — specifically through ABSTRACTION LAYERS?

The conjecture: a useful graph would let the agent operate at the right
level of detail. Coarse summary for the parts of the problem that are
context, fine detail for the parts that matter right now. Like reading
a textbook — chapter summaries to orient, then drilling into one
section.

If this works, the comparison is:

- **Baseline:** load N isolated relevant notes (no graph).
- **Graph-aware:** load 1 detailed note + N-1 one-line summaries of
  neighbors, with the option to expand any neighbor on demand.

**Status: no signal yet.** B11 didn't need any abstraction structure —
every question matched to one note and the note answered it
completely. The benchmark we'd need:

- A task where the right answer requires *both* a specific detail AND
  awareness of how it fits into a larger structure.
- Where the larger structure is too big to fully load.
- Where loading neighbors as summaries (vs full notes) is the lever
  that separates "fits in budget" from "doesn't fit".

We have not designed such a benchmark.

---

## Q4. Is the graph better than flat context + retrieve-a-few-notes?

Restatement of Q3 in measurement terms: against a strong
isolated-notes baseline, does adding edges and structured traversal
produce a measurable accuracy or cost win?

**Status: no signal yet.** B11 compared structured store vs
ad-hoc-file, not structured-with-graph vs structured-without-graph.
To answer this we'd need (b) implemented as a clean baseline —
multiple notes, semantic retrieval, no edges, no graph walk — and run
it side-by-side with (c).

---

## What's missing

To make progress on Q2(b), Q3, and Q4 we need:

1. A "flat multi-note" baseline implementation, so the graph version
   isn't being compared to a markdown-file straw man.
2. A benchmark where abstraction layers plausibly help — likely a
   debugging-style task where the agent needs to zoom out and zoom in
   across a structure (call graph, dependency tree, layered
   architecture).
3. A benchmark where edges plausibly help — e.g. "find all facts that
   contradict this one" or "trace the chain from X to Y" — queries
   that flat retrieval would have to brute-force.

Until those exist, the honest position is: memory across sessions
helps (Q1); the graph specifically has not yet been shown to do work
beyond what isolated notes would do.
