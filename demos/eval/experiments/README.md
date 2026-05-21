# Experiments index

Durable record of the memory research. Each sub-folder is one
experiment; this file is the one-glance summary.

See `PLAN.md` for the full plan, the questions being answered, the
memory variants studied (NONE / SINGLE / MULTI / LINKED / HIER), and
the stop conditions.

## Status legend

- ⬜ planned
- 🟨 running
- ✅ done — pass (matched hypothesis)
- ❌ done — fail (didn't match)
- ⏸️ paused / stopped mid-run
- 🗄️ superseded (kept for record only)

## Current plan (post-pivot to filesystem-based memory variants)

| ID | Name | Q | Variants | Status | Headline |
|----|------|---|----------|--------|----------|
| e10 | NONE vs SINGLE on bug recall | Q1 | NONE, SINGLE | ❌ fail (nuanced) | SINGLE p2 -43%, but +70% p1 capture cost → net +10% total on one follow-up. Memory pays per-query, loses on one-shot. |
| e20 | SINGLE vs MULTI | Q2 | SINGLE, MULTI | ⬜ planned | — |
| e25 | multi-vector vs single-vector vs grep on recall stress | Q2 | grep, single, multi | ✅ PASS | multi recall@1 86% vs single 56% (+30pp); recall@5 100% vs 98%. With thinking disabled, Sonnet jumps to **92%** recall@1 at same latency. |
| e25b | same task with Haiku sub-agent | (opt) | multi-haiku | ⚠️ trade-off | Haiku w/ thinking: 82% recall@1, 995s. Haiku w/o thinking: 74% recall@1, 321s. Sonnet-w/o-thinking dominates on recall (92%) at similar latency. Production: keep Sonnet, disable thinking. |
| e30 | MULTI vs LINKED on chained queries | Q4 | MULTI, LINKED | ⬜ planned | — |
| e40 | MULTI vs HIER under budget | Q3 | MULTI, HIER | ⬜ planned | — |
| e50 | Cheaper-model replication | (opt) | winners | ⬜ planned | — |
| e60 | Amortization curve | (meas) | winners | ⬜ planned | — |

All e10–e60 use only the agent's existing Read / Write / Bash / Glob
/ Grep tools, with memory structure defined entirely in the prompt.

## Superseded (kept for record)

| ID | Name | Why superseded |
|----|------|----------------|
| e01 | Realistic baseline (used memory-graph MCP) | Research scope pivoted: not studying any specific MCP. e01 also hit an MCP-ergonomics bug (`content` vs `body`) that contaminated its result. |
| e01b | Same as e01 with explicit MCP schema | Started but stopped after the scope pivot; partial run only. |

Empty stub folders `e02_*`, `e03_*`, `e04_*`, `e05_*`, `e06_*`
remain on disk from the pre-pivot draft. New experiments use the
e10–e60 numbering so they don't clash; old stub folders can be
deleted when convenient.

## Prior exploratory work

In `../lab/` is the original scratch (B1–B11). Most informative was
**B11** — first showed that structured memory (multi-file) beats
single-file markdown by ~2.7× on phase-2 cost. That is essentially
the SINGLE vs MULTI question on this codebase; e20 will revisit it
cleanly.

## How to add an experiment

1. `mkdir experiments/eNN_short_name/`
2. Write a README with hypothesis / setup / pass criterion (see e10
   when it exists for the template).
3. Add a row to the table above.
4. After running, fill in the experiment's README result + reflection
   sections AND update the status emoji + headline above.

## Designing adaptively

The plan is a scaffold, not a schedule. After every experiment,
reflect (see `PLAN.md` "Reflection loop") before designing the next.
Replacing or skipping planned experiments based on findings is
expected.
