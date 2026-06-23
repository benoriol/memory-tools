Route a piece of knowledge to the right paper-memory destination and apply that destination's gating. What to capture: $ARGUMENTS

The single smart entry point for the paper profile. It does not contain write mechanics; each
destination's command owns its protocol, and this only classifies and delegates, so the rules
live in one place and cannot drift. Research analog of `/mem`.

**1. Classify.** From $ARGUMENTS plus recent context, pick the destination(s). One capture can
fan out to several.

| If the content is... | Destination | Command | Gating |
|---|---|---|---|
| a specific run / result (numbers, recipe, paths) | detail leaf + `experiments.md` | `/mem-log` | low |
| ...and I asked for it to be paper-critical | + `experiments_important.md` (the `**Important:**` flag) | `/mem-log` | medium — explicit ask |
| durable methodology / operational knowledge / a gotcha | `technical_notes/` + its index | `/mem-note` | low new, medium edit |
| a thematic paper claim / argument | `paper_narrative.md` | `/mem-canon` | high, sentence-by-sentence |

If it is genuinely ambiguous or spans destinations, ask one short routing question. Do not guess.

**Ask whenever anything is unclear.** Not just the route: if a number, a path, whether this
supersedes an existing note, whether a run is paper-critical, or the intended wording is
ambiguous, stop and ask a short follow-up before writing. A quick question is always cheaper than
a wrong note or a mis-filed run. Asking never counts against you; committing a guess does.

**2. Announce + confirm the route.** State the destination(s), the file, and the gating in one
line, e.g. "-> mem-log (detail + experiments.md, low), Important: no; also suggest mem-canon if
this backs a claim." Get a quick OK on the routing before any irreversible write. This is only
the routing gate; each command's own gating still applies inside its protocol.

**3. Delegate.** For each destination, read its command file (`/mem-log`, `/mem-note`,
`/mem-canon`) and follow it with the same content rather than reimplementing the steps here. Run
the low-friction writes first; for the narrative, run its advise-first, sentence-by-sentence flow
rather than writing directly.

**4. Shallow audit always runs.** Every route includes its command's consistency check. Never
finalize a write that contradicts, duplicates, or silently supersedes an existing leaf, index
entry, or narrative claim; flag the conflict (what and where) and ask first. The deep version is
`/mem-audit`.

**Always:** never write `paper_narrative.md` without explicit sentence-by-sentence approval;
never flag a run `**Important:**` without an explicit ask; never invent numbers or paths; if your
confidence in the route is low, ask. The standalone writers still work directly when you already
know where something goes; this is the convenience layer over them.
