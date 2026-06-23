Audit the paper memory for inconsistencies. Scope / note (optional): $ARGUMENTS

Cross-check the narrative and indexes against the experiment **detail leaves** (the source of
truth) and report a punch-list. **Never silently fix:** propose, then apply only after I approve
(narrative fixes route to `/papernote`, index fixes to `/paper-index`). Research analog of
`/mem-audit`.

**Scope.** No argument: exhaustive — `paper_narrative.md` + `experiments_important.md` +
`experiments.md` + `technical_notes.md` vs all of `experiments/` and `technical_notes/`. With an
argument: narrow to it (a claim/section, a method, a setting, a date range, a file, or a free-text
concern).

**Check for:**
1. **Index drift** — `experiments.md` / `technical_notes.md` not matching the leaves on disk
   (missing entry, stale pointer, wrong order). Fix by running `/paper-index`.
2. **Important-subset drift** — `experiments_important.md` not matching the set of leaves flagged
   `**Important:** yes` (an entry present that is not flagged, or a flagged leaf missing). Fix by
   rerunning `/paper-index experiments`; if the *flag itself* is wrong, that is a `/logexp` edit
   to the leaf.
3. **Number drift** — every figure in the narrative / important index matches its cited detail
   leaf (report both values and locations).
4. **Missing fields** — leaves with no `**Headline:**`, notes with no `**Summary:**` (they index
   as `(... needed)`).
5. **Dangling links** — cross-references or narrative evidence links pointing at a moved or
   deleted leaf.
6. **Orphans** — important-subset entries not cited anywhere in the narrative; notable
   `experiments/` results surfaced nowhere; narrative claims with no evidence link down to a leaf.
7. **Stale "results pending"** — leaves whose headline still says pending but whose body now has
   numbers.
8. **Contradictions / recipe mixing** — two leaves incompatible on the same (method, setting,
   metric); a narrative claim contradicted by a later run; or a headline table that silently
   mixes recipes/configs.

**Report** each finding as: type · location(s) · the conflict · a suggested fix.

**Correction policy.** Detail leaves are truth. Fix a wrong recorded result with a NEW dated
superseding leaf (cross-linked), not a silent edit; narrative fixes go through `/papernote`;
index fixes through `/paper-index`; a wrong `**Important:**` flag is fixed on the leaf via
`/logexp`. Apply only after I approve.
