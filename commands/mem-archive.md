Archive notes that are no longer current: propose first, move only after my confirmation. Optional focus or explicit targets: $ARGUMENTS

Moves leaves out of the live stores into `_archive/`, so they drop out of the indexes (and out of
always-on context) without being deleted. Nothing moves until I confirm.

**1. Resolve.** Root = `MEM_ROOT` env var, else `./project_notes`. The archive is
`<root>/_archive/`, mirroring the original path: `journal/2026/06/x.md` goes to
`_archive/journal/2026/06/x.md`. It sits outside the store folders, so `/mem-index` never lists it.

**2. Pick candidates.** With $ARGUMENTS: explicit paths are the candidates; free text (a topic, a
date range, "older than 3 months", a store) narrows the search. Without: scan the indexes and the
leaves they point to for notes that are superseded, obsolete, abandoned, or long untouched and no
longer referenced. Never pick `canon/` leaves on age alone; archive canon only when it is plainly
superseded.

**3. Propose, in exactly this format, nothing else.** Letter the candidates A, B, C, ...:
```
A. <path> -> _archive/<path>
   Why: <reason, one line>. Linked from: <paths, or "none">.
```
No preamble, no roll-up. If nothing is worth archiving, say so in one line. Then stop and wait: I
reply with the letters to archive (or "all" / "none").

**4. Execute only the confirmed letters.** For each: create the mirrored folder under `_archive/`,
`git mv` the leaf (plain `mv` if the root is not tracked), and leave its content unchanged. Then
fix inbound links that point at it: in `journal/` and `knowledge/` leaves, repoint the link to the
archive path; in `canon/`, do not edit, just list the affected lines and suggest `/mem-canon`.

**5. Reindex.** Run `/mem-index` on every store you touched. Report what moved, where (absolute
paths), and which links you repointed or left for `/mem-canon`.

**Always:** propose first, move only confirmed items; move, never delete; never edit an archived
note's content; never touch `CLAUDE.md`. To restore a note, move it back and rerun `/mem-index`.
