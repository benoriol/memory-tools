# e03 — Chained-relation queries

**Question:** Q4 — does graph traversal beat flat multi-note retrieval
on queries that *require* following relationships?

## Hypothesis

When questions require multi-hop reasoning over relationships, Arm C
(graph + `memory_neighbors`) beats Arm B (flat semantic notes) on
either accuracy or cost — because Arm B has to grep/load many
candidate notes to traverse a chain that Arm C can walk directly.

If this hypothesis fails (C ≈ B on chained queries), the graph layer's
relational machinery is not earning its keep, and the tool should be
simplified to flat multi-note storage.

## Why this experiment

e02 will likely show C ≈ B on point lookups. e03 is the design that
gives the graph a fair shot at contributing. If C still doesn't beat B
here, that's a strong negative result.

## Setup

**Corpus:** synthetic 50-module project with an *explicit dependency
graph* seeded in docstrings:

```
module_07 docstring: "calls into module_12, module_15"
module_12 docstring: "calls into module_19"
module_19 docstring: "emits event SchemaChanged"
module_15 docstring: "calls into module_18"
...
```

The dependency graph is generated deterministically so the grader
knows the ground-truth reachable set from any node.

**Phase 1 (investigate):**
- Same prompt as e01/e02 for arm B.
- For arm C, prompt adds: "When you capture a module's behavior, ALSO
  capture which other modules it depends on. Use the relationship
  fields available in memory_capture."

**Phase 2 (chain queries):** 20 questions of three flavors:
1. **Downstream reach** ("If module_07 fails, which modules' behavior
   is affected?") — requires forward traversal.
2. **Path query** ("Trace the call chain from module_03 to the
   SchemaChanged event") — requires path-finding.
3. **Upstream cause** ("Which modules can cause the FrameDropped event
   to fire?") — requires reverse traversal.

Grader checks the *set* of modules in the answer matches the
ground-truth set (Jaccard ≥ 0.8 per question for hit).

## Arms

| Arm | Tools |
|-----|-------|
| B (flat) | Read, Bash, Grep + memory_capture/search/retrieve/get (no memory_neighbors) |
| C (graph) | above + memory_neighbors + memory_remember |

## Metrics

- Accuracy: hits / 20 (Jaccard ≥ 0.8 per question).
- Phase 2 cost, time, tokens.
- **Tool call profile**: for arm C, count `memory_neighbors` calls.
  If zero, the graph wasn't used and the result is uninformative.
- **Hop depth observed**: for arm C, log the depth at which each
  neighbors call was made (1-hop, 2-hop, ...).

## Pass criterion

- C accuracy − B accuracy ≥ 0.15 (15-percentage-point improvement),
  OR
- C cost ≤ 0.7 × B cost at equal accuracy.

Either suffices. If neither holds AND `memory_neighbors` was called
≥10 times, the graph genuinely doesn't help — strong negative result.

If `memory_neighbors` was called <5 times, the experiment failed to
exercise the graph and needs a stronger prompt or task design.

## How to run

```bash
cd demos/eval/experiments/e03_chained_relations
python e03.py --arm B
python e03.py --arm C
```

Expected runtime: ~10 minutes (2 arms × 2 phases).

## Result

> ⬜ Not yet run.
>
> | | B (flat) | C (graph) |
> |---|---|---|
> | Accuracy | — / 20 | — / 20 |
> | Phase 2 cost | — | — |
> | memory_neighbors calls | 0 (disabled) | — |
> | Mean hop depth | n/a | — |

## Conclusion

> Fill in. Critical question: did the graph actually fire? If yes, did
> it help? If no, why not — was the prompt insufficient or did the
> agent route around it?
