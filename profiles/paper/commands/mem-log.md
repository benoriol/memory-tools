Log an experiment: one run or result, as a detail leaf plus its index pointers. Optional note: $ARGUMENTS

Record one experiment (a training run, an inference/eval, a benchmark, an ablation) as a **detail
file** (the full write-up, the source of truth) plus a **compact pointer** in the index, then
refresh the indexes. Low gating: append after a shallow consistency check. This is the research
analog of `/mem-log`.

**1. Resolve + place.** Root = `MEM_ROOT` env, else `./project_notes`. The leaf goes at
`experiments/YYYY-MM-DD-<slug>.md` using today's date and a short kebab slug unique within
`experiments/`.

**2. Write the detail leaf.** H1 `# YYYY-MM-DD — <title>`, then the fields, in this order so the
index can be regenerated from them:
- `**Why:**` <one sentence> — the motivation; also shown in the index.
- `**Headline:**` <one line> — the single most important result/number; also shown in the index.
  If results are not in yet, write `**Headline:** results pending`.
- `**Important:**` yes | no — whether this run is paper-critical and belongs in
  `experiments_important.md`. Default **no**; set **yes** only when I ask for it in my own words
  (read the intent, don't keyword-match) or it is plainly a headline result. When in doubt, no.
Then the fields that apply: **Type** (training / inference / both), **Setup** (only what differs
from the canonical recipe; link methodology, don't restate it), **Result** (the numbers, a table
if comparing), **Paths** (config, checkpoint, output/inference dir, logs, run-tracking link),
**Cross-references** (relative links to related leaves), **Note** ($ARGUMENTS verbatim, if any).
Pull numbers and paths from the conversation and the files; never invent a number or a path —
write "results pending" / "TBD" instead.

**3. Shallow consistency check.** Read the directly-related leaves (same method + setting +
claim) and any `paper_narrative.md` claim this touches. If the result contradicts, duplicates, or
conflicts with a recorded one, ask before finalizing rather than guessing. (Narrow check; the
full sweep is `/mem-audit`.)

**4. Refresh the indexes.** Run `/mem-index experiments` so the leaf appears at the tail of
`experiments.md`, and in `experiments_important.md` iff it is flagged `**Important:** yes`.

**5. Narrative hand-off.** If the result is paper-relevant (changes or backs a claim), suggest
`/mem-canon` with a one-line note on where it would fit. Never write `paper_narrative.md` from
here.

**Always:** experiments are append-friendly, but never overwrite an existing leaf; never invent
numbers or paths; keep `**Why:**` and `**Headline:**` to one line each; promotion to the
important subset happens only through the `**Important:**` flag, never by hand-editing the index.
