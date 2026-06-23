Scaffold a research project's paper memory, wire the contract into CLAUDE.md, and optionally migrate existing notes. Optional args: a target notes root and/or existing sources to migrate (e.g. `./project_notes migrate NOTES.md docs/`). $ARGUMENTS

Sets up the flat, paper-oriented layout the other paper commands use (`/mem-log`, `/mem-note`,
`/mem-canon`, `/mem`, `/mem-suggest`, `/mem-audit`, `/mem-index`), makes the always-read
contract live in `CLAUDE.md`, and (when pointed at existing material) reorganises that material
into the structure. Scaffolding is idempotent and non-destructive; migration is proposal-first and
never bulk-writes. This is the research sibling of `/mem-init`: experiments instead of a journal, a
paper-critical "important" subset, technical notes instead of knowledge, and a paper narrative
instead of canon. There is no separate spine file: the always-on rules live in a managed block in
`CLAUDE.md` (which the harness always loads), and the per-destination detail lives in the command
files and is read when you use them.

**Phase A — Scaffold (always).** Resolve the root: a path in $ARGUMENTS, else the `MEM_ROOT`
env var, else `./project_notes`. State the absolute path and what you will create before
creating it. Create if missing:
- `experiments/` — the per-run detail leaves (the source of truth).
- `experiments.md` — the full chronological index: a one-line header plus an empty managed block
  (the `mem-index` markers, `regenerate with /mem-index experiments`).
- `experiments_important.md` — the paper-critical subset index, header plus an empty managed block.
- `technical_notes/` — durable methodology / operational notes.
- `technical_notes.md` — its index, header plus an empty managed block.
- `paper_narrative.md` — the curated paper argument, as a skeleton (no invented results): a title
  `# <project> — paper narrative`, a one-line "source of truth = detail files; maintained via
  /mem-canon, sentence-gated" note, then empty sections **TL;DR (abstract) · Method · Main results
  · Ablations · Supplementary · Open / pending**.
Never overwrite an existing store, index, or note; report what already existed. Empty managed
block template:
```
# experiments index
<!-- mem-index: managed block; regenerate with /mem-index experiments. Do not hand-edit between the markers. -->

<!-- /mem-index -->
```

**Phase B — Wire the contract into CLAUDE.md (always).** In `./CLAUDE.md` (create if missing),
insert or refresh the managed block below, touching nothing outside the markers. This block is the
spine — the only always-on memory context — so keep it tight:
```
<!-- mem:begin (managed by memory-commands) -->
## Memory (paper notes)
Before substantive work, read these always-on indexes under project_notes/ (override the root
with MEM_ROOT): technical_notes.md, paper_narrative.md, and experiments_important.md (the
paper-critical run subset). The full run history is experiments.md (on-demand) with detail leaves
under experiments/ — open them when you need a specific run rather than reasoning from the
narrative's summaries.

Destinations and gating: experiments/ + experiments.md (dated run leaves; low; append-only) ·
experiments_important.md (the paper-critical subset; a projection of each leaf's **Important:**
yes|no flag, rebuilt by /mem-index, never hand-edited) · technical_notes/ (durable
methodology/gotchas; low to add, medium to edit) · paper_narrative.md (the curated paper argument;
high, sentence-by-sentence approval). Capture with /mem-log, /mem-note, /mem-canon, or /mem to
route; run /mem-index after any write. Keep the always-on set lean: only paper-critical runs
earn the important subset; everything else stays one fetch away in experiments.md.

Notes are fallible: detail leaves are the source of truth; verify against them and raise any
inconsistency you notice (a narrative number that no longer matches its leaf, a dangling link, a
stale "results pending", an important entry not flagged on its leaf) on the spot with what and
where, rather than silently fixing it. The exhaustive sweep is /mem-audit.
<!-- mem:end -->
```
If the block already exists, replace only what is between the markers; never duplicate it.

**Phase C — Build the context model for THIS project (always).** Before placing anything, reason
explicitly, as a context engineer, about this specific project. The principle: everything
always-loaded (the CLAUDE.md block, the technical-notes index, the narrative, the important
subset) is paid on every task, while the full experiments index and every detail leaf cost only a
fetch; the indexes carry a one-line pointer per entry, so the existence and gist of every run are
always known even when its body is not. Judge what every task here needs always-on (the paper's
thesis and headline claims, the core evaluation methodology, the load-bearing recipe, the handful
of paper-critical runs) versus what belongs in on-demand leaves (every individual run, deep
methodology). State the resulting model in a sentence or two: what you keep always-on, what you
leave to recall, and why, and your initial criterion for which runs are "important".

**Phase D — Migrate existing material (only if sources are given).** When $ARGUMENTS points at
existing notes (a `NOTES.md`, a `docs/` pile, a lab log, scattered `.md`, a results spreadsheet):
1. **Inventory** the sources and read them.
2. **Propose a mapping** as a table: each chunk -> destination (an `experiments/` leaf with a
   date+slug, a `technical_notes/` leaf, the CLAUDE.md block for methodology/rules, the paper
   narrative, or "leave out" with a reason). Mark which runs you recommend flagging **Important**
   (paper-critical) versus ordinary, with the tradeoff stated. Flag duplicates and contradictions.
3. **Get approval** on the mapping before writing anything.
4. **Execute through the writers**, each at its own gating: route runs as in `/mem-log`,
   methodology as in `/mem-note`, paper claims as in `/mem-canon` (advise-first, sentence-by-
   sentence; never bulk-write the narrative). Pull numbers and paths from the sources; never
   invent.
5. **Non-destructive:** leave originals in place unless I say move them. At the end, report what
   was migrated and where, and what you deliberately left out and why.
6. Run `/mem-index` to rebuild every index you touched.

**Always:** non-destructive; never overwrite a leaf or bulk-write the narrative; edit `CLAUDE.md`
only between the managed markers; report what existed, what you created, and what you placed in
recall versus always-on, each with absolute paths.
