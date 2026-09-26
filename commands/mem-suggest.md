Survey the work so far and suggest what is worth capturing, without writing anything. Optional focus: $ARGUMENTS

The read-only, advisory sibling of `/mem`. It never writes, logs, or edits any file; the only
output is a short lettered list of actions (new, edit, delete) and where each would go. Think
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

**4. Turn candidates into actions (shallow).** Read the relevant indexes (`journal.md`,
`knowledge.md`, `canon.md`) and, where needed, the leaf itself. Each candidate becomes one action:
**NEW** (nothing covers it), **EDIT** (a leaf exists but the conversation has newer, extra, or
conflicting info), or **DELETE** (a leaf is now wrong, superseded, or a duplicate). Drop anything
already captured. Index level plus the touched leaves only; the exhaustive sweep is `/mem-audit`.

**5. Report in exactly this format, nothing else.** Letter the actions A, B, C, ... in order:
```
A. NEW <path> · <command>
   <what to write, one line>
B. EDIT <path> · <command>
   Now: <what the leaf says, short>. Change: <what to change>. Why: <reason>.
C. DELETE <path>
   Why: <reason>.
```
One or two short lines per action: enough for me to understand it with minimal context, no
more. No preamble, no roll-up, no next-step advice. If nothing is worth capturing, say so
in one line.

**Always:** suggest, never write. Touch no leaf, no index, no `canon/`. Never invent numbers or
paths; if a result is not in the conversation, write "numbers not in context".
