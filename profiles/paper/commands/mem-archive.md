Archive experiments and technical notes that are no longer current: propose first, move only after my confirmation. Optional focus or explicit targets: $ARGUMENTS

Moves leaves out of the live destinations into `_archive/`, so they drop out of the indexes (and
out of always-on context) without being deleted. Nothing moves until I confirm.

**1. Resolve.** Root = `MEM_ROOT` env var, else `./project_notes`. The archive is
`<root>/_archive/`, mirroring the original path: `experiments/2026-06-01-x.md` goes to
`_archive/experiments/2026-06-01-x.md`. It sits outside `experiments/` and `technical_notes/`,
so `/mem-index` never lists it. `paper_narrative.md` is never archived.

**2. Pick candidates.** With $ARGUMENTS: explicit paths are the candidates; free text (a method, a
setting, a date range, "older than 3 months") narrows the search. Without: scan the indexes and
the leaves they point to for runs and notes that are superseded (a later run replaces it),
abandoned (a dead-end direction), broken (a bug invalidated it), or long untouched and no longer
referenced. Flag any candidate marked `**Important:** yes` or cited by `paper_narrative.md`;
those need a narrative change first.

**3. Propose, in exactly this format, nothing else.** Letter the candidates A, B, C, ...:
```
A. <path> -> _archive/<path>
   Why: <reason, one line>. Linked from: <paths, or "none">. [Important / cited by narrative]
```
No preamble, no roll-up. If nothing is worth archiving, say so in one line. Then stop and wait: I
reply with the letters to archive (or "all" / "none").

**4. Execute only the confirmed letters.** For each: create the mirrored folder under `_archive/`,
`git mv` the leaf (plain `mv` if the root is not tracked), and leave its content unchanged. Then
fix inbound links that point at it: in `experiments/` and `technical_notes/` leaves, repoint the
link to the archive path; in `paper_narrative.md`, do not edit, just list the affected lines and
suggest `/mem-canon`.

**5. Reindex.** Run `/mem-index` so the archived leaves leave `experiments.md`,
`experiments_important.md`, and `technical_notes.md`. Report what moved, where (absolute paths),
and which links you repointed or left for `/mem-canon`.

**Always:** propose first, move only confirmed items; move, never delete; never edit an archived
note's content; never touch `CLAUDE.md` or bulk-edit the narrative. To restore a note, move it
back and rerun `/mem-index`.
