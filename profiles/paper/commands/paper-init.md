Scaffold a research project's paper memory, wire the contract into CLAUDE.md, and optionally migrate existing notes. Optional args: a target notes root and/or existing sources to migrate (e.g. `./project_notes migrate NOTES.md docs/`). $ARGUMENTS

Sets up the flat, paper-oriented layout the other paper commands use (`/logexp`, `/technote`,
`/papernote`, `/note`, `/whattonote`, `/paper-audit`, `/paper-index`), makes the always-read
contract live, and (when pointed at existing material) reorganises that material into the
structure. Scaffolding is idempotent and non-destructive; migration is proposal-first and never
bulk-writes. This is the research sibling of `/mem-init`: experiments instead of a journal, a
paper-critical "important" subset, technical notes instead of knowledge, and a paper narrative
instead of canon.

**Phase A — Scaffold (always).** Resolve the root: a path in $ARGUMENTS, else the `MEM_ROOT`
env var, else `./project_notes`. State the absolute path and what you will create before
creating it. Create if missing:
- `experiments/` — the per-run detail leaves (the source of truth).
- `experiments.md` — the full chronological index, header plus an empty managed block (the
  `mem-index` markers).
- `experiments_important.md` — the paper-critical subset index, header plus an empty managed
  block.
- `technical_notes/` — durable methodology / operational notes.
- `technical_notes.md` — its index, header plus an empty managed block.
- `paper_narrative.md` — the curated paper argument (skeleton; see Phase B).
Never overwrite an existing store, index, or note; report what already existed.

**Phase B — Write the spine** at `<root>/README.md` (only if missing) and the
`paper_narrative.md` skeleton. Keep the spine short; it is always-read. Include: the tier model
(spine / always-read indexes / on-demand leaves); the **four destinations** and their gating
(experiments, the important subset, technical notes, paper narrative); the experiment-leaf
format and the technical-note format (below); the read-first contract; the "notes are fallible,
flag inconsistencies on sight" clause; and the **context model** below, close to verbatim,
since every command reasons from it:
> **Context model.** The window is finite and everything always-loaded is paid on every task.
> Always loaded: the spine, the technical-notes index, the paper narrative, and the
> **important-experiments** index. On-demand: the full experiments index and every detail leaf,
> the individual technical notes, loaded only when fetched. The indexes carry the full set plus
> a one-line pointer per entry, so the existence and gist of every experiment are always known
> even when its body is not; that is what makes deferring to recall safe. The important subset
> exists precisely because the full experiments index grows without bound: only the paper-
> critical runs earn permanent always-on cost; everything else stays one fetch away in
> `experiments.md`. When unsure, leave a run out of the important subset and keep the always-on
> set lean.

The `paper_narrative.md` skeleton is the paper outline only (no invented results): `# <project>
— paper narrative`, a one-line "source of truth = detail files; maintained via /papernote,
sentence-gated" note, then empty sections **TL;DR (abstract) · Method · Main results · Ablations
· Supplementary · Open / pending**.

**Phase C — Wire the contract into CLAUDE.md (always).** In `./CLAUDE.md` (create if missing),
insert or refresh a managed block, touching nothing outside the markers:
```
<!-- mem:begin (managed by memory-commands) -->
## Memory (paper notes)
Before substantive work, read project_notes/README.md, the technical-notes index, the paper
narrative, and experiments_important.md (the paper-critical run subset). The full run history is
project_notes/experiments.md (on-demand) with detail leaves under experiments/; open them when
you need a specific run rather than reasoning from the narrative's summaries. Notes can be
stale: detail leaves are the source of truth, verify against them and raise inconsistencies on
sight.
<!-- mem:end -->
```
If the block already exists, replace only what is between the markers; never duplicate it.

**Phase D — Build the context model for THIS project (always).** Before placing anything,
reason explicitly, as a context engineer, about this specific project using the model in the
spine. Judge what every task here needs always-on (the paper's thesis and headline claims, the
core evaluation methodology, the load-bearing recipe, the handful of paper-critical runs) versus
what is detail that belongs in on-demand leaves (every individual run, deep methodology). State
the resulting model in a sentence or two: what you keep always-on, what you leave to recall, and
why, and your initial criterion for which runs are "important".

**Phase E — Migrate existing material (only if sources are given).** When $ARGUMENTS points at
existing notes (a `NOTES.md`, a `docs/` pile, a lab log, scattered `.md`, a results
spreadsheet):
1. **Inventory** the sources and read them.
2. **Propose a mapping** as a table: each chunk -> destination (an `experiments/` leaf with a
   date+slug, a `technical_notes/` leaf, the spine for methodology/rules, the paper narrative,
   or "leave out" with a reason). Mark which runs you recommend flagging **Important** (paper-
   critical) versus ordinary, with the tradeoff stated. Flag duplicates and contradictions.
3. **Get approval** on the mapping before writing anything.
4. **Execute through the writers**, each at its own gating: route runs as in `/logexp`,
   methodology as in `/technote`, paper claims as in `/papernote` (advise-first, sentence-by-
   sentence; never bulk-write the narrative). Pull numbers and paths from the sources; never
   invent.
5. **Non-destructive:** leave originals in place unless I say move them. At the end, report what
   was migrated and where, and what you deliberately left out and why.
6. Run `/paper-index` to rebuild every index you touched.

**Always:** non-destructive; never overwrite a leaf or bulk-write the narrative; edit `CLAUDE.md`
only between the managed markers; report what existed, what you created, and what you placed in
recall versus always-on, each with absolute paths.
