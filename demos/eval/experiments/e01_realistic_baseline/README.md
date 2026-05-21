# e01 — Realistic baseline replication

**Question:** Q1 — does memory help across the session boundary, on a
realistic setup, on a *different* task type than B11?

## Hypothesis

When the corpus stays on disk and the no-memory agent is free to use
Write/Edit as its own scratch, the memory_graph arm beats the
no-memory arm on phase-2 cost by ≥2× at ≥95% accuracy on both arms.

## Why this experiment

B11 already showed a 2.7× cost win on architectural-fact recall, but
the no-memory arm voluntarily wrote a single flat markdown file. We
want to (a) confirm the result generalizes to a different task and
(b) measure how the no-memory agent organizes its filesystem-scratch
when the task isn't "document architectural facts".

## Setup

**Domain:** synthetic bug-investigation. A 30-module Python codebase
where each module's function bodies contain exactly one planted bug
(off-by-one, swapped arguments, missing null check, wrong default,
etc.). Bug ground-truth is held in the test harness (not written to
disk) so the agent has to find each bug by *reading the code*, not by
grepping a label.

(Spec deviation: README originally said 60 modules / 30 questions.
v1 uses 30 modules / 30 questions — one bug per module, all queried —
for a first conclusive read; scale up if the result is ambiguous.)

**Phase 1 (investigate):** "Investigate every module. Identify the bug
in each. A different agent will be asked diagnostic questions
tomorrow — leave behind whatever notes you find useful." Both arms
have Write/Edit/Bash/Read/Glob/Grep. With-memory arm additionally has
`mcp__memory-graph__*` tools.

**Between phases:** nothing deleted. Workdir contains all source +
whatever notes the agent wrote + `.memory-graph/` (if applicable).

**Phase 2 (diagnose):** 30 paraphrased questions about specific bugs:
"Which module has a null-pointer issue in its retry path?", "What is
the off-by-one error in the pagination logic?" Output is a strict
`Q01: <module_NN, one-line bug description>` format.

**Each phase = one fresh `query()` call.** No in-context carryover.

## Arms

| Arm | Tools |
|-----|-------|
| `no_memory` | Read, Bash, Glob, Grep, Write, Edit |
| `with_memory` | above + `mcp__memory-graph__*` (init'd .memory-graph/) |

## Metrics

- **Accuracy**: hits / 30 (grader checks `module_NN` mention plus
  presence of the canonical bug-type keyword).
- **Phase 1 cost** ($), **phase 2 cost** ($) — both reported separately.
- **Phase 1 tokens, phase 2 tokens** — split by input/output/cache.
- **Wall time** per phase.
- **Notes written by no_memory arm**: post-phase-1, list all non-source
  files the agent created; record their total size.
- **Memory notes in with_memory arm**: count of files in
  `.memory-graph/notes/`.

## Pass criterion (declared in advance)

- Both arms ≥ 28/30 accuracy.
- `with_memory` phase-2 cost ≤ 0.5 × `no_memory` phase-2 cost.

Either of these missed = fail. Failure is fine, just document why.

## How to run

```bash
cd demos/eval/experiments/e01_realistic_baseline
python e01.py 2>&1 | tee run.log
```

Expected runtime: ~5 minutes (both arms, both phases).

## Result (run 1, 2026-05-21)

| | no_memory | with_memory |
|---|---|---|
| Accuracy | **29 / 30** | **30 / 30** |
| Phase 1 cost | $0.231 | $0.274 |
| Phase 2 cost | **$0.054** | **$0.081** |
| Phase 1 time | 107s | 190s |
| Phase 2 time | 30s | 68s |
| Scratch file written p1 | `bug_notes.md` (122 lines) | `BUG_NOTES.md` (156 lines) |
| Memory notes captured | n/a | **0** |
| Total cost | **$0.285** | **$0.355** |

**Verdict: FAIL.** Accuracy criterion passed (both ≥ 28/30) but cost
criterion failed (with_memory was 28% *more* expensive than
no_memory, not 50% cheaper).

## Reflection

### What we expected
Memory tools beat the agent's natural filesystem fallback by ≥2× on
phase-2 cost.

### What actually happened
- **Both arms used the same realistic fallback**: a single flat
  markdown file (`bug_notes.md` for no_memory, `BUG_NOTES.md` for
  with_memory).
- The with_memory arm called `memory_capture_batch` once but the
  store ended up with **0 notes**. The capture silently failed.
- with_memory still ran the full investigation and wrote a markdown
  scratch file anyway — defensive behavior from the agent.
- Phase 2 with_memory called `memory_retrieve` once, got nothing
  useful (store was empty), then fell back to reading the markdown
  file via Bash + Read.
- Net: with_memory paid for the wasted memory-tool attempts plus the
  same filesystem strategy no_memory used. Hence: more expensive.

### Why memory_capture_batch failed
Direct MCP probe (separate from the agent) revealed the actual error:

```
Error executing tool memory_capture_batch:
Store.capture() got an unexpected keyword argument 'content'
```

The store's `capture()` signature requires `title`, `summary`, `body`,
`kind` as required fields. The agent naturally reached for `content`
(the obvious default for "note text"), and `kind` may have been
omitted. The error was returned to the agent but apparently not
recovered from — the agent gave up and went to the filesystem.

The agent's choice of `content` is a sane LLM default — it's the most
common field name across note-taking APIs. The tool's choice of `body`
+ required `kind` is an ergonomic trap.

### What this implies
1. **The experiment did not isolate the research question.** We
   measured "memory tool failure vs filesystem fallback", not "memory
   vs filesystem".
2. **There's a real ergonomic finding here**: the memory_capture
   tools' field schema is non-obvious to an LLM and they fail silently
   from the agent's perspective. This is worth a product fix
   independently of the research.
3. **Tool deferral overhead**: the agent had to call `ToolSearch` to
   discover the memory tool schemas (they were deferred at session
   start). That's 1-2 extra round trips per phase that the no_memory
   arm doesn't pay.

### Next steps (designed adaptively, not from the original plan)

Three follow-ups, in priority order:

- **e01b — Replicate with explicit schema in the prompt.** Spell out
  the exact field names (`title, summary, body, kind`) in
  PHASE1_PROMPT. Also instruct the agent to verify via
  `memory_status` after batching and retry if count is 0. This
  isolates "does memory help when actually populated?" from the tool
  ergonomic issue.
- **(eM) Tool ergonomics: alias `content` → `body` in the server.**
  Product fix, not a research experiment. Worth filing.
- **e01c — If e01b passes, replicate with NO explicit schema hint to
  see if the agent recovers from the first capture error on its
  own.** This measures real-world reliability, not just
  best-case-prompt performance.

For now, proceed to e01b. e01c is contingent.

## Run-1 artifacts

- `e01_results.json` — full result blob with usage/cost/tool-call
  profiles per arm.
- `run.log` — stdout from the run.
- Workdirs preserved at `/tmp/lab-bench/e01-*-20260521-102*/` for
  inspection (will be reclaimed on tmpfs cleanup).
