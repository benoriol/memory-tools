Survey the work so far and suggest what is worth capturing, without writing anything. Optional focus: $ARGUMENTS

The read-only, advisory sibling of `/mem`. It never writes, logs, or edits any file; the only
output is a short bullet summary of what you would capture and where each piece would go. Think
"what would `/mem` find here if I ran it now?" Useful when several capturable things have piled
up over a session.

**1. Scope.** No argument: audit the whole conversation for anything capturable. With an
argument: narrow to it ($ARGUMENTS can be a store, a topic, a date, or a free-text concern).
Source is the conversation only; do not sweep the filesystem or git for this.

**2. Collect candidates.** Walk the conversation and pull out each distinct piece of knowledge
the memory would want: a dated event or result, a durable method or gotcha, a decision or shift
in the project story. One concept per bullet; merge duplicates; drop idle chatter.

**3. Classify each the way `/mem` does.** For every candidate name the store, the folder path,
the command, and the gating:

| If the item is... | Store | Command | Gating |
|---|---|---|---|
| a dated event or result | `journal/` | `/mem-log` | low |
| durable methodology / a gotcha | `knowledge/` | `/mem-note` | low new, medium edit |
| project story / a decision | `canon/` | `/mem-canon` | high, line-by-line |

**4. Dedup against the indexes (shallow).** Read the relevant store indexes (`journal.md`,
`knowledge.md`, `canon.md`) and tag each
item NEW (nothing covers it), ALREADY-CAPTURED (point to the leaf), or UPDATES (a leaf exists
but the conversation has newer or conflicting info). Index level only; the exhaustive sweep is
`/mem-audit`.

**5. Report, bullets only.** One bullet per item: `<description>` -> `<store/path>` ·
`<command>` · `<gating>` · `<NEW / ALREADY-CAPTURED / UPDATES>`. Then a one-line roll-up of the
files that would be touched if you captured all NEW items, and a suggested next step (e.g. "run
/mem on items 1-3; item 4 is already covered"). If nothing is worth capturing, say so in one
line.

**Always:** suggest, never write. Touch no leaf, no index, no `canon/`. Never invent numbers or
paths; if a result is not in the conversation, write "numbers not in context".
