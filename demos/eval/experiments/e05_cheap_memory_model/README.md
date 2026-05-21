# e05 — Cheaper model for memory operations

**Question:** does using Haiku for the memory sub-agents
(`memory_remember`, `memory_retrieve`) preserve the cost win at lower
cost than using Sonnet for everything?

## Hypothesis

The memory sub-agents perform constrained, well-scoped tasks
(summarize-and-store; retrieve-and-format). Haiku 4.5 should handle
these adequately. Swapping Sonnet → Haiku for the sub-agents should
reduce total cost by ≥30% with ≤5% accuracy regression.

## Why this experiment

This is a practical optimization. The main agent's reasoning quality
matters; the sub-agent's quality matters less because it's doing
mechanical work. If Haiku works, the production recommendation becomes
"use Haiku for memory ops, Sonnet for the orchestrator."

## Setup

Use the **e01** benchmark verbatim (60-module bug-investigation, two
phases, paraphrased queries). Same corpus generator, same questions,
same grader. Only the sub-agent model changes.

Implementation note: the Agent SDK's `memory_remember` and
`memory_retrieve` orchestration spawns nested `query()` calls. We need
to thread a model override through. Look at
`src/memory_graph/orchestration/` — the `remember.py` and
`retrieve.py` files set up `ClaudeAgentOptions(model=...)` for the
sub-agent. Confirm this is configurable (likely via env var or
parameter) before running.

If it isn't currently configurable: add a `MEMORY_GRAPH_SUBAGENT_MODEL`
env var that defaults to the main model. That's a small code change
worth making first.

## Arms

| Arm | Main agent | Memory sub-agents |
|-----|-----------|-------------------|
| `C-sonnet` | Sonnet 4.6 | Sonnet 4.6 |
| `C-haiku-mem` | Sonnet 4.6 | Haiku 4.5 |

Both arms use full memory_graph (all tools including
`memory_neighbors` and `memory_remember`). We're not testing whether
memory helps — we know it does (Q1). We're testing whether the
sub-agent model matters.

## Metrics

- Accuracy (e01 grader).
- Total cost, broken down: **main-agent cost** vs **sub-agent cost**.
  This requires logging which `query()` calls are from sub-agents —
  the orchestration layer should already tag these.
- Wall time per phase.

## Pass criterion

- `C-haiku-mem` accuracy ≥ `C-sonnet` accuracy − 5 percentage points.
- `C-haiku-mem` total cost ≤ 0.7 × `C-sonnet` total cost.

Both required.

## Sensitivity / variants to consider

If the simple swap passes, try the more aggressive variants:

- **C-haiku-everywhere**: Haiku for main agent too. Probably regresses
  on the trickier questions; useful to know the cost/quality floor.
- **C-haiku-capture-only**: Haiku for `memory_remember`, Sonnet for
  `memory_retrieve`. Tests whether retrieval needs the smarter model
  more than capture does.

These are stretch experiments — only run if e05 main result passes.

## How to run

```bash
cd demos/eval/experiments/e05_cheap_memory_model
# Confirm sub-agent model is overridable; add env var support if not.
MEMORY_GRAPH_SUBAGENT_MODEL=claude-sonnet-4-6 python e05.py --tag sonnet
MEMORY_GRAPH_SUBAGENT_MODEL=claude-haiku-4-5-20251001 python e05.py --tag haiku
```

Expected runtime: ~10 minutes per arm.

## Result

> ⬜ Not yet run.
>
> | | C-sonnet | C-haiku-mem |
> |---|---|---|
> | Accuracy | — / 30 | — / 30 |
> | Main-agent cost | — | — |
> | Sub-agent cost | — | — |
> | Total cost | — | — |
> | Phase 2 time | — | — |

## Conclusion

> Fill in. If pass: update `templates/claude_protocol.md` or the
> server's defaults to use Haiku for sub-agents. If fail: where did
> Haiku break — capture quality, retrieval quality, or both?
