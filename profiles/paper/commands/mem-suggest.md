Survey the work so far and suggest what is worth capturing, without writing anything. Optional focus: $ARGUMENTS

The read-only, advisory sibling of `/mem`. It never writes, logs, or edits any file; the only
output is a short bullet summary of what you would capture and where each piece would go. Think
"what would `/mem` find here if I ran it now?" Useful when several capturable things have piled
up over a session. Research analog of `/mem-suggest`.

**1. Scope.** No argument: audit the whole conversation for anything capturable. With an
argument: narrow to it ($ARGUMENTS can be a method, a setting, a date/run, a topic, or a free-text
concern). Source is the conversation only; do not sweep the filesystem or git for this.

**2. Collect candidates.** Walk the conversation and pull out each distinct piece the paper
memory would want: a finished or attempted run (numbers / recipe / paths), a durable methodology
or gotcha, a thematic paper claim or shift in the argument. One concept per bullet; merge
duplicates; drop idle chatter and half-formed ideas that did not land.

**3. Classify each the way `/mem` does.** For every candidate name the destination, the command,
and the gating:

| If the item is... | Destination | Command | Gating |
|---|---|---|---|
| a specific run / result | detail leaf + `experiments.md` | `/mem-log` | low |
| ...and it looks paper-critical | + `experiments_important.md` | `/mem-log` | medium, explicit ask |
| durable methodology / a gotcha | `technical_notes/` + its index | `/mem-note` | low new, medium edit |
| a thematic paper claim | `paper_narrative.md` | `/mem-canon` | high, sentence-by-sentence |

One item can fan out to several destinations; say so when it does, and flag any you think is
Important (paper-critical).

**4. Dedup against the indexes (shallow).** Read the relevant indexes (`experiments.md`,
`experiments_important.md`, `technical_notes.md`) and tag each item NEW (nothing covers it),
ALREADY-CAPTURED (point to the leaf), or UPDATES (a leaf exists but the conversation has newer or
conflicting info). Index level only; the exhaustive sweep is `/mem-audit`.

**5. Report, bullets only.** One bullet per item: `<description>` -> `<destination>` ·
`<command>` · `<gating>` · `<NEW / ALREADY-CAPTURED / UPDATES>` · `<flag if Important>`. Then a
one-line roll-up of the files that would be touched if you captured all NEW items, and a suggested
next step (e.g. "run /mem on items 1-3; item 4 is already covered"). If nothing is worth
capturing, say so in one line.

**Always:** suggest, never write. Touch no leaf, no index, no `paper_narrative.md`, no
`CLAUDE.md`. Never invent numbers or paths; if a run's results are not in the conversation, write
"numbers not in context". It only points at the gated destinations; the actual approval still
happens inside `/mem-log` / `/mem-canon` when you choose to run them.
