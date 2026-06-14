Log a journal entry: a dated event or result. Optional note: $ARGUMENTS

Record one thing that happened (a run, a deploy, an incident, a result) as a dated leaf in the
journal store, then refresh the index. Low gating: append after a shallow consistency check.

**1. Resolve + place.** Root = `MEM_ROOT` env, else `./project_notes`. The leaf goes at
`journal/YYYY/MM/YYYY-MM-DD-<slug>.md` using today's date and a short kebab slug unique within
that month.

**2. Write the leaf.** H1 `# YYYY-MM-DD <title>`, then `**Summary:** <one line>` (this is what
the index shows), then the fields that apply: **Why**, **What happened**, **Result** (the
numbers, a table if comparing), **Paths** (configs, dashboards, logs, artifacts),
**Cross-references** (relative links to related leaves), **Note** ($ARGUMENTS verbatim, if
any). Pull numbers and paths from the conversation and the files; if results are not in yet,
write "results pending". Never invent a number or a path.

**3. Shallow consistency check.** Read the directly-related recent entries and any `canon/`
claim this touches. If the result contradicts, duplicates, or conflicts with a recorded one,
ask before finalizing rather than guessing. (Narrow check; the full sweep is `/mem-audit`.)

**4. Refresh the index.** Run `/mem-index journal` so the new leaf appears at the tail.

**5. Canon hand-off.** If the result changes a decision or the project story, suggest
`/mem-canon` with a one-line note on where it would fit. Never write `canon/` from here.

**Always:** journal is append-friendly, but never overwrite an existing leaf; never invent
numbers or paths; keep the summary to one line.
