# e02 — Storage shape A/B/C ablation

**Question:** Q2 — what storage shape is best? Single file vs flat
multi-note vs full graph.

## Hypothesis

- B (flat multi-note) beats A (single file) on cost, because granular
  retrieval avoids loading the full corpus per query.
- B and C (graph) tie on this task, because the questions are
  independent point lookups — graph traversal has nothing to do.

A confirmed B>>A would justify continuing past flat retrieval.
A confirmed B≈C would tell us the graph layer is doing no work *on
this task type* — Phase 3 (e03/e04) is then the test of whether it
ever does.

## Why this experiment

B11 conflated "memory helps" with "structured memory beats single
file". This experiment cleanly separates the three storage strategies
on the same task.

## Setup

Same corpus and phase-1/phase-2 protocol as **e01**. The only
difference is per-arm tool/prompt configuration.

### Arm A — single file

- Tools: Read, Bash, Glob, Grep, Write, Edit. No memory tools.
- Phase 1 prompt explicitly instructs: "Maintain ALL your notes in a
  single file called `MEMORY.md`. Do not create any other notes file.
  Append to MEMORY.md as you investigate."
- Phase 2 prompt: "Your prior notes are in `MEMORY.md`. Read it once
  and answer the questions."
- Realism note: this *is* a realistic strategy — many developers
  maintain a `NOTES.md` file. It's just less granular than B/C.

### Arm B — flat multi-note (no graph)

- Tools: Read, Bash, Glob, Grep, Write, Edit + a **restricted** memory
  toolset: `memory_capture`, `memory_capture_batch`, `memory_search`,
  `memory_retrieve`, `memory_get`. Crucially: **no `memory_neighbors`,
  no `memory_remember`**.
- Effectively: semantic per-note storage with no relational traversal.
- Phase prompts identical to with_memory in e01.

### Arm C — full graph

- Tools: all of B plus `memory_neighbors` and `memory_remember`.
- Phase prompts identical to with_memory in e01.

## Metrics

Same as e01, plus:
- **Memory tool call profile**: count of each `memory_*` tool called
  per arm. We want to see if Arm C *actually* uses `memory_neighbors`,
  or if the agent skips it because the task doesn't need it.

## Pass criterion

- (B-vs-A): B's phase-2 cost ≤ 0.7 × A's phase-2 cost, both ≥ 28/30.
- (B-vs-C): no pre-declared pass. Reporting: |C-B|/B for cost and
  accuracy. Flag as "graph contributes" if C beats B by ≥15% in cost
  *and* the agent actually called `memory_neighbors`.

## How to run

```bash
cd demos/eval/experiments/e02_storage_shape_ablation
python e02.py --arm A
python e02.py --arm B
python e02.py --arm C
# or
python e02.py --all
```

Expected runtime: ~15 minutes (3 arms × 2 phases).

## Result

> ⬜ Not yet run. Three-column comparison after running:
>
> | | A (single file) | B (flat notes) | C (graph) |
> |---|---|---|---|
> | Accuracy | — / 30 | — / 30 | — / 30 |
> | Phase 1 cost | — | — | — |
> | Phase 2 cost | — | — | — |
> | Total cost | — | — | — |
> | memory_neighbors calls | n/a | 0 (disabled) | — |

## Conclusion

> Fill in. Specifically address:
> - Does B beat A? By how much?
> - Does C add anything over B on this task?
> - If C doesn't help here, that's evidence the graph layer is dormant
>   for point-lookup workloads — feed this into the e03/e04 design.
