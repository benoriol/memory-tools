# project_notes (paper memory spine)

Always-read map for this research project's memory. Read this plus the always-read indexes
before substantive work, then follow the pointers to the leaves you actually need.

## Tiers
- **Spine** (this file): rules + map. Always read.
- **Always-read indexes**: `technical_notes.md`, `paper_narrative.md`, and
  `experiments_important.md` (the paper-critical run subset). Small and load-bearing.
- **On-demand**: `experiments.md` (the full run history) and every detail leaf under
  `experiments/`; the individual notes under `technical_notes/`. Read when fetched.

## Destinations and gating
- `experiments/` + `experiments.md` — one dated detail leaf per run (the source of truth) plus a
  full chronological index. Low gating. Written via `/logexp`.
- `experiments_important.md` — the paper-critical subset, a pure projection of the leaves flagged
  `**Important:** yes`. Medium gating (explicit ask sets the flag). Rebuilt by `/paper-index`.
- `technical_notes/` + `technical_notes.md` — durable methodology / operational knowledge. Low to
  add, medium to edit. Written via `/technote`.
- `paper_narrative.md` — the curated paper argument. High gating, sentence-by-sentence approval.
  Written via `/papernote`.

## Experiment-leaf format
```
# YYYY-MM-DD — <title>
**Why:** <one line, shown in the index>
**Headline:** <the single most important number, shown in the index>
**Important:** yes | no    (yes -> also in experiments_important.md)
**Type:** training | inference | both
**Setup:** <only what differs from the canonical recipe>
**Result:** <numbers; a table if comparing>
**Paths:** <config, checkpoint, output dir, logs, run-tracking link>
**Cross-references:** <relative links to related leaves>
```
`**Why:**`, `**Headline:**`, and `**Important:**` are the source of truth for the index entries,
so the indexes regenerate from the leaves and never drift.

## Technical-note format
```
# <Title>
**Summary:** <one line, copied into the index>

<terse bullets / short sections>
```

## Notes are fallible
The notes can be stale or wrong. Use them actively, but when it matters verify against the code,
configs, and results rather than trusting a note. The detail leaves under `experiments/` are the
source of truth; the narrative and the indexes only summarize and point. If while working you
notice anything off (a narrative number that no longer matches its leaf, a dangling link, a stale
"results pending", an important entry that is not flagged on its leaf), raise it right away with
what and where, and suggest a fix; do not silently fix it. The exhaustive version is
`/paper-audit`.

## Context model
The window is finite and everything always-loaded is paid on every task. Always loaded: this
spine, the technical-notes index, the paper narrative, and the important-experiments index.
On-demand: the full experiments index and every detail leaf, the individual technical notes,
loaded only when fetched. The indexes carry the full set plus a one-line pointer per entry, so
the existence and gist of every experiment are always known even when its body is not; that is
what makes deferring to recall safe. The important subset exists precisely because the full
experiments index grows without bound: only the paper-critical runs earn permanent always-on
cost; everything else stays one fetch away in `experiments.md`. When unsure, leave a run out of
the important subset and keep the always-on set lean.
