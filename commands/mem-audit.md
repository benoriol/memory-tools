Audit the memory for inconsistencies. Scope / note (optional): $ARGUMENTS

Cross-check the indexes and `canon/` against the leaves (the source of truth) and report a
punch-list. **Never silently fix:** propose, then apply only after I approve (canon fixes route
to `/mem-canon`, index fixes to `/mem-index`).

**Scope.** No argument: exhaustive across all three stores. With an argument: narrow to it (a
store, a folder, a topic, a date range, or a free-text concern).

**Check for:**
1. **Index drift** — a `<store>/index.md` that does not match the files on disk (missing leaf,
   stale entry, wrong tree). Fix by running `/mem-index <store>`.
2. **Missing summaries** — leaves with no `**Summary:**` line (they index as `(summary needed)`).
3. **Dangling links** — cross-references or canon evidence links pointing at a moved or deleted
   leaf.
4. **Orphans** — notable leaves surfaced nowhere; canon claims with no evidence link down to a
   leaf.
5. **Stale "results pending"** — journal leaves that said pending but whose content now has
   numbers.
6. **Contradictions** — two leaves incompatible on the same point; or a canon statement
   contradicted by a later journal entry.

**Report** each finding as: type, location(s), the conflict, and a suggested fix.

**Correction policy.** Leaves are truth. Fix a wrong recorded result with a new dated journal
leaf that supersedes it (cross-linked), not a silent edit; canon fixes go through `/mem-canon`;
index fixes through `/mem-index`. Apply only after I approve.
