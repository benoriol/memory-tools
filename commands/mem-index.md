Rebuild a store's full-tree index from the notes on disk. Optional store (journal / knowledge / canon; default all): $ARGUMENTS

The hybrid index builder. The tree comes from the filesystem, so it never drifts
structurally; each note's summary comes from its own `**Summary:**` field, so summaries have a
single source of truth. The index is **regenerated from the leaves, not merged** with the old
index, which makes it deterministic and idempotent. Safe to run as the last step of any write.

**1. Resolve.** Root = `MEM_ROOT` env var, else `./project_notes`. Stores = $ARGUMENTS if
given, else all three.

**2. Walk the store.** Recursively list every `.md` leaf under the store, excluding `index.md`
and any folder-level `README.md` (handled in step 4). Note slugs contain no spaces, so each
emitted line stays unambiguous.

**3. Read each leaf's pointer.** From each leaf take its H1 title and its first `**Summary:**`
line. If the summary line is missing, use `(summary needed)` and collect that path for the
report. Never invent a summary.

**4. Emit the managed block.** Rewrite `<store>/index.md`, replacing only the text between the
`mem-index` markers and preserving anything outside them. Represent the hierarchy with
two-space indentation per depth level:
- a folder as `<name>/`, plus its summary if the folder has a `README.md` with one
- a leaf as `<name>  <summary>` (the file's slug, two spaces, then the summary text)

Order alphabetically, except `journal/`, which is chronological oldest-first so the most
recent entries sit at the tail. Example for `knowledge`:
```
arch/                      model architecture
  attention.md             MHA shapes + KV-cache layout
  io/
    caching.md             disk cache format + invalidation
eval/
  metrics.md               how runs are scored
```

**5. Report.** State the resolved index path (absolute), how many leaves were indexed, and any
leaf still missing a `**Summary:**`. Optionally note what changed versus the previous block,
for information only; the block content always comes from the leaves regardless.

**Always:** regenerate from the leaves; touch only the managed block; never create, move, or
delete a note here (that is the writers' job).
