# project_notes (memory spine)

Always-read map for this project's memory. Read this plus the relevant store `index.md`
before substantive work, then follow the tree to the leaves you actually need.

## Tiers
- **Spine** (this file): rules + map. Always read.
- **Indexes** (`<store>/index.md`): full tree + one-line summaries, auto-built by `/mem-index`.
  Always read.
- **Leaves**: the detail notes, nested in folders. Read on demand via an index.

## Stores and gating
- `journal/` — dated run/event logs. Low gating. Chronological; recent is the tail.
- `knowledge/` — durable methods, facts, gotchas. Low to add, medium to edit. Topic tree.
- `canon/` — project story, key decisions, rationale. High gating, sentence-level approval.

## Leaf format
```
# <title>
**Summary:** <one line, copied into the index>

<details>
```
The summary is the source of truth for the index entry, so the index never drifts from the notes.

## Notes are fallible
The notes can be stale or wrong. Use them actively, but when it matters verify against the
code, files, and results rather than trusting a note over what you can observe. If while
working you notice anything off (a note that contradicts the code or another note, a number
that no longer matches, a dangling link, a stale "results pending"), raise it to the user right
away with what and where, and suggest a fix; do not silently fix it. This surface-level check
runs continuously, whenever you happen to encounter something; the deliberate, exhaustive
version is `/mem-audit`.

## Context model
The window is finite and everything always-loaded is paid on every task. Always loaded: this
spine, the knowledge and canon indexes, and the journal tail. Recall: every leaf, loaded only
when fetched. The indexes carry the full tree plus a one-line summary, so the existence and
gist of every leaf are always known even when its body is not; that is what makes deferring to
recall safe. Decide placement by expected cost: promote into always-on context only what is
small, needed on most tasks, and costly to miss (the vision, a core invariant, a load-bearing
decision); everything else is a leaf, where the only cost of leaving it out is one fetch and
the index still surfaces it. When unsure, prefer a leaf and keep the always-on set lean.
