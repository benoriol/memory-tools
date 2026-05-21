# e01b — Same task, explicit memory tool schema in prompt

**Question:** does memory help across the session boundary, when the
agent is actually able to use the memory tools correctly?

## Why this exists

`e01` failed its cost criterion not because memory lost on merit but
because the with_memory arm couldn't actually use the tools: it called
`memory_capture_batch` with `content` (the LLM-natural field name)
instead of `body` (the tool's required field), got a silent error,
and fell back to filesystem-as-scratch. So e01 measured "broken
memory vs filesystem", not "memory vs filesystem". We need to fix the
prompt so the comparison is honest.

See `../e01_realistic_baseline/README.md` for the full reflection
that motivated this experiment.

## Difference from e01

Three changes:

1. **PHASE1_PROMPT spells out the schema** for memory_capture_batch
   explicitly:
   `{"title": str, "summary": str, "body": str, "kind": str, "tags": [str]}`.
2. **PHASE1_PROMPT instructs the agent to verify**: call
   `memory_status` after the batch, and if `total_nodes == 0`,
   retry with corrected payload before falling back.
3. Phase 2 prompt is unchanged — we want the *retrieval* behavior to
   stay as natural as possible.

Everything else is identical to e01.

## Hypothesis

When the memory tool is actually populated, with_memory phase-2 cost
drops to ≤ 0.5 × no_memory phase-2 cost at ≥ 95% accuracy on both
arms.

If this passes: e01's "FAIL" was an ergonomics issue, and memory
genuinely helps when usable.

If this also fails: memory's design loses to single-flat-file even
when it's working. That's a much more interesting negative result —
the multi-note structured store doesn't beat the single-file
fallback on this task.

## Pass criterion

Same as e01: both arms ≥ 28/30 accuracy, with_memory phase-2 cost ≤
0.5 × no_memory phase-2 cost.

Additionally: with_memory MUST have ≥ 25 memory notes captured by end
of phase 1. If <25, the prompt-fix didn't work and we need to keep
iterating before drawing conclusions.

## Result

> ⬜ Pending run.

## Reflection

> To fill in after running.
