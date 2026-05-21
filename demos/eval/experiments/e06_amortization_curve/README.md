# e06 — Amortization curve

**Question:** capture costs are paid once; retrieval savings are paid
per query. At what number of queries / sessions / corpus size does
memory pay back?

## Hypothesis

Memory's total-cost advantage over the natural-filesystem baseline:

- Grows with **number of phase-2 queries** (more queries = more
  retrievals share the capture cost).
- Grows with **number of capture sessions** (memory accumulates;
  filesystem notes get harder to maintain).
- Grows with **corpus size** (re-investigation becomes more expensive
  for the no-memory arm).

The output of this experiment is not a pass/fail but a *curve* — three
plots that let us state, with numbers, "for tasks above X queries (or
Y sessions, or Z corpus size), use memory."

## Why this experiment

Every prior experiment was at one operating point. This is the only
one that produces a continuous recommendation. It's how we move from
"memory helps in one specific setup" to "here's when to use memory."

## Setup

Reuse e01's task (bug-investigation, paraphrased questions). Three
sweeps, varying one axis at a time:

### Sweep A — phase-2 query count

Fixed: 60 modules, 1 capture session.
Vary: number of questions ∈ {10, 30, 100, 300}.

For 300 questions: generate 10× the e01 question pool by varying the
paraphrase. Grade each independently.

### Sweep B — capture session count

Fixed: 60 modules, 30 questions in final session.
Vary: number of investigate-only sessions before the final query
session ∈ {1, 3, 10}.

Each capture session has the agent investigate a *new chunk* of the
codebase (modules 0-19, then 20-39, then 40-59) so memory genuinely
accumulates.

### Sweep C — corpus size

Fixed: 30 questions, 1 capture session.
Vary: module count ∈ {30, 100, 300, 1000}. Questions adapted to
sample uniformly across the corpus.

## Arms (each point in every sweep)

| Arm | |
|-----|-|
| `baseline` | No memory tools. Agent uses Write/Edit as in e01. |
| `memory` | Full memory_graph (the e05 winner — Haiku sub-agents if e05 passes; otherwise all-Sonnet). |

So each sweep produces N×2 runs.

## Metrics

For each (sweep, point, arm) combination:

- Accuracy.
- Total cost.
- Phase-2 cost only.
- Wall time.

Headline output:

- **Sweep A plot**: cost vs query-count, two lines (baseline, memory).
  Intersection point = "break-even queries".
- **Sweep B plot**: cost vs session-count.
- **Sweep C plot**: cost vs module-count.

## Pass criterion

This is a measurement experiment. Success = three useful plots and a
recommendation table that looks like:

```
For Q queries on a C-module corpus, memory is worthwhile when:
  Q ≥ Q*(C)
```

with Q*(C) populated from the sweep data.

The only way this *fails* to be useful is if the curves cross weirdly
or are dominated by noise. To control noise: run each point twice and
report mean.

## How to run

```bash
cd demos/eval/experiments/e06_amortization_curve
python e06.py --sweep A
python e06.py --sweep B
python e06.py --sweep C
```

Expected runtime: ~2-3 hours total. This is the most expensive
experiment in the plan — run last.

## Resource note

The corpus=1000 point in Sweep C will allocate ~1MB of synthetic
source. RAM-wise fine (32GB cap is comfortable), but the agent's
phase-2 (no-memory) cost on this point may be substantial — budget
$5-10 for this single point.

## Result

> ⬜ Not yet run.
>
> Sweep A — query count:
>
> | Queries | baseline $ | memory $ | ratio |
> |---------|-----------|----------|-------|
> | 10 | — | — | — |
> | 30 | — | — | — |
> | 100 | — | — | — |
> | 300 | — | — | — |
>
> Sweep B — session count:
>
> | Sessions | baseline $ | memory $ | ratio |
> |----------|-----------|----------|-------|
> | 1 | — | — | — |
> | 3 | — | — | — |
> | 10 | — | — | — |
>
> Sweep C — corpus size:
>
> | Modules | baseline $ | memory $ | ratio |
> |---------|-----------|----------|-------|
> | 30 | — | — | — |
> | 100 | — | — | — |
> | 300 | — | — | — |
> | 1000 | — | — | — |

## Conclusion

> Fill in with the recommendation table and any inflection points.
> This becomes the practitioner-facing answer: "use memory when…".
