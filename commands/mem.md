Route a piece of knowledge to the right store and apply that store's gating. What to capture: $ARGUMENTS

The single smart entry point. It does not contain write mechanics; each store's command owns
its protocol, and this only classifies and delegates, so the rules live in one place and cannot
drift.

**1. Classify.** From $ARGUMENTS plus recent context, pick the destination(s). One capture can
fan out to several.

| If the content is... | Store | Command | Gating |
|---|---|---|---|
| a dated event or result (a run, deploy, incident, number) | `journal/` | `/mem-log` | low |
| durable methodology, a fact, or a gotcha | `knowledge/` | `/mem-note` | low new, medium edit |
| the project story, a decision, or rationale | `canon/` | `/mem-canon` | high, line-by-line |

If it is genuinely ambiguous or spans stores, ask one short routing question. Do not guess.

**2. Announce + confirm the route.** State the destination(s), the folder path, and the gating
in one line, e.g. "-> mem-note (knowledge/arch/caching, new leaf, low); also suggest mem-canon
if this changes a decision." Get a quick OK on the routing before any irreversible write. This
is only the routing gate; each command's own gating still applies inside its protocol.

**3. Delegate.** For each destination, follow its command (`/mem-log`, `/mem-note`,
`/mem-canon`) with the same content; read its command file and follow it rather than
reimplementing the steps here. Run the low-friction writes first; for `canon`, run its
advise-first, line-by-line approval flow rather than writing directly.

**4. Shallow audit always runs.** Every route includes its command's consistency check. Never
finalize a write that contradicts, duplicates, or silently supersedes an existing leaf, index
entry, or canon statement; flag the conflict (what and where) and ask first. The deep version
is `/mem-audit`.

**Always:** never write `canon/` without explicit line-by-line approval; never invent numbers
or paths; if your confidence in the route is low, ask. The standalone writers still work
directly when you already know where something goes; this is the convenience layer over them.
