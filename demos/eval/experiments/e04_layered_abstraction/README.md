# e04 — Layered abstraction under context budget

**Question:** Q3 — does loading neighbors as *summaries* (instead of
full notes) help when the context budget is tight?

## Hypothesis

When the agent has a hard limit on retrieved tokens, the strategy of
"load one full detail-note + N short summary-of-neighbor-notes" beats
"load top-K full notes" on accuracy at equal token cost.

The intuition: real debugging needs both the specific function detail
*and* awareness of the surrounding subsystem. Flat top-K retrieval
forces a choice; layered retrieval can mix resolutions.

## Why this experiment

This is the strongest claim the graph could make. If we can show that
abstraction-layered retrieval recovers accuracy that flat retrieval
loses under budget, the graph layer earns a structural justification.

If it ties flat retrieval — even under budget — the layered approach is
not actually contributing.

## Setup

**Corpus:** hierarchical 200-module project. 20 subsystems of 10
modules each. Every module has both:

- A **detail docstring**: specifics of the implementation (constants,
  function signatures, special cases).
- A **subsystem summary** (stored on the parent subsystem note): "this
  subsystem handles X; its modules cooperate by Y".

Total corpus ~400KB. Larger than B11 but still fits in 1M context — the
*budget* is the lever, not corpus size.

**Phase 1 (capture):** prompt instructs the agent to write both
detail-level notes and subsystem-summary notes, and to link them via
parent/child relations (for arm C-layered) or as flat notes (for arms
B-loose and B-tight).

**Phase 2 (mixed-level questions):** 30 questions that *require both
levels of context*. Example: "Why does module_037 silently swallow
exceptions in its retry path? Frame your answer in terms of the
subsystem's overall error-handling philosophy."

A grader rubric (LLM-as-judge with a fixed-checkpoint Sonnet call)
scores each answer on (a) detail accuracy, (b) structural awareness,
(c) overall coherence. Scale 0-3 each, max 9.

## Arms

| Arm | Retrieval strategy | Token budget |
|-----|-------------------|--------------|
| `B-loose` | top-K full notes via memory_search, K=10 | unlimited |
| `B-tight` | top-K full notes via memory_search, K=3 | ~3 × full-note size |
| `C-layered` | 1 full detail note + 5 neighbor summaries | same as B-tight |

The budget for `B-tight` and `C-layered` should be identical in tokens
— that's what makes the comparison fair. We'll measure actual tokens
retrieved per question.

## Metrics

- **Grader score**: mean rubric score (0-9) per arm.
- **Tokens retrieved per question** (we want B-tight and C-layered to
  be within 10% of each other).
- **Cost, time** per arm.

## Pass criterion

- `C-layered` mean rubric score ≥ `B-loose` − 1.0 (i.e. layered nearly
  matches the loose flat retrieval), AND
- `C-layered` mean rubric score ≥ `B-tight` + 1.5 (i.e. clearly beats
  the same-budget flat baseline).

If both hold, the layering is doing real work: it recovers accuracy
without paying B-loose's token bill.

## How to run

```bash
cd demos/eval/experiments/e04_layered_abstraction
python e04.py --arm B-loose
python e04.py --arm B-tight
python e04.py --arm C-layered
```

Expected runtime: ~20-25 minutes (3 arms × 2 phases on a larger corpus).

## Open implementation question

How to actually enforce the token budget for `B-tight` and `C-layered`?
Options:

1. **Prompt instruction**: "retrieve at most N tokens of context."
   Unreliable.
2. **Wrapper tool**: write a `bounded_search` that calls
   `memory_search` and truncates results to N tokens before returning.
   Clean but artificial.
3. **K control + measure**: set K and measure resulting token count.
   Most natural but doesn't enforce an exact budget.

Plan: start with option 3 (set K=3 for B-tight; for C-layered, set
neighbors=5 with summaries-only). Measure actual tokens. Iterate if
budgets diverge.

## Result

> ⬜ Not yet run.
>
> | | B-loose | B-tight | C-layered |
> |---|---|---|---|
> | Rubric score | — / 9 | — / 9 | — / 9 |
> | Tokens / question | — | — | — |
> | Cost | — | — | — |

## Conclusion

> Fill in. The decisive question: did layering recover the accuracy
> that B-tight lost? If yes, abstraction-layered graph retrieval has a
> demonstrated use case. If no, retiring the abstraction story is
> warranted.
