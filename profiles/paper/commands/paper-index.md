Rebuild the paper-memory indexes from the leaves on disk. Optional target (experiments / technical / all; default all): $ARGUMENTS

The hybrid index builder for the paper profile. The set of entries comes from the filesystem, so
it never drifts structurally; each entry's pointer text comes from fields inside the leaf itself,
so there is a single source of truth. Every index is **regenerated from the leaves, not merged**
with the old index, which makes it deterministic and idempotent. It rebuilds three managed
blocks: `experiments.md`, `experiments_important.md`, and `technical_notes.md`. It never touches
`paper_narrative.md` (that is curated, owned by `/papernote`). Safe to run as the last step of
any write.

**1. Resolve.** Root = `MEM_ROOT` env var, else `./project_notes`. Target = $ARGUMENTS if given
(`experiments` rebuilds both experiment indexes; `technical` rebuilds the technical-notes index),
else all.

**2. Experiments — read each leaf's pointer.** List every `.md` under `experiments/`. From each
leaf take, from the fields just under the H1: the H1 title (`# YYYY-MM-DD — <title>`), the
`**Why:**` line, the `**Headline:**` line, and the `**Important:**` flag (yes/no; absent = no).
If `**Headline:**` is missing use `(headline needed)` and collect that path for the report; never
invent a headline or a number.

**3. Emit the two experiment blocks.** Rewrite the managed block in `experiments.md` with one
compact block per leaf, **chronological oldest-first** (most recent at the tail), exactly:
```
## YYYY-MM-DD — <title>

**Why:** <why line>
**Headline:** <headline line>
→ [details](experiments/<slug>.md)
```
No tables or path dumps in the index — it points. Then rewrite the managed block in
`experiments_important.md` with the **same blocks filtered to `**Important:** yes`**, same order.
The important subset is therefore a pure projection of the leaves and can never drift from them;
to add or drop a run from it, change that leaf's `**Important:**` flag and rerun, never hand-edit
the block.

**4. Technical notes — read each leaf's pointer.** List every `.md` under `technical_notes/`
(excluding the index). From each take its H1 title and its first `**Summary:**` line (missing ->
`(summary needed)`, collect the path). Rewrite the managed block in `technical_notes.md`,
alphabetical, one entry each:
```
## [<Title>](technical_notes/<slug>.md)
<summary line>
```

**5. Markers.** In every index, replace only the text between the
`<!-- mem-index: ... -->` and `<!-- /mem-index -->` markers; preserve everything outside them
(the header, any methodology note). If a target index file or its markers are missing, say so
rather than guessing where the block goes.

**6. Report.** State each rebuilt index path (absolute), how many entries it now holds (and, for
experiments, how many are flagged important), and any leaf missing a `**Headline:**` or
`**Summary:**`. Optionally note what changed versus the previous block, for information only.

**Always:** regenerate from the leaves; touch only the managed blocks; never create, move, or
delete a leaf, and never edit `paper_narrative.md` here (those are the writers' job).
