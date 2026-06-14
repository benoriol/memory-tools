Scaffold a project's memory, wire the contract into CLAUDE.md, and optionally migrate existing notes. Optional args: a target notes root and/or existing sources to migrate (e.g. `./project_notes migrate docs/ NOTES.md`). $ARGUMENTS

Sets up the three-store layout the other `/mem-*` commands use, makes the always-read contract
live, and (when pointed at existing material) reorganises that material into the structure.
Scaffolding is idempotent and non-destructive; migration is proposal-first and never bulk-writes.

**Phase A — Scaffold (always).** Resolve the root: a path in $ARGUMENTS, else the `MEM_ROOT`
env var, else `./project_notes`. State the absolute path and what you will create before
creating it. Create if missing: `journal/`, `knowledge/`, `canon/`, each with an `index.md`
that is just its header plus an empty managed block (the `mem-index` markers). Never overwrite
an existing store, index, or note; report what already existed.

**Phase B — Write the spine** at `<root>/README.md` (only if missing). Keep it short; it is
always-read. Include: the three-tier model (spine / indexes / leaves); the three stores and
their gating; the leaf format (`# title`, `**Summary:**`, details); the read-first contract;
the "notes are fallible, flag inconsistencies on sight" clause; and the **context model**
below, close to verbatim, since every command reasons from it:
> **Context model.** The window is finite and everything always-loaded is paid on every task.
> Always loaded: the spine, the knowledge and canon indexes, the journal tail. Recall: every
> leaf, loaded only when fetched. The indexes carry the full tree plus a one-line summary, so
> the existence and gist of every leaf are always known even when its body is not; that is what
> makes deferring to recall safe. Decide placement by expected cost: promote into always-on
> context only what is small, needed on most tasks, and costly to miss (the vision, a core
> invariant, a load-bearing decision); everything else is a leaf, where the only cost of
> leaving it out is one fetch and the index still surfaces it. When unsure, prefer a leaf and
> keep the always-on set lean.

**Phase C — Wire the contract into CLAUDE.md (always).** In `./CLAUDE.md` (create if missing),
insert or refresh a managed block, touching nothing outside the markers:
```
<!-- mem:begin (managed by memory-commands) -->
## Memory
Before substantive work, read project_notes/README.md and the relevant <store>/index.md, then
follow the tree to the leaves you need. The spine explains the context model and gating. Notes
can be stale: verify against reality and raise inconsistencies on sight.
<!-- mem:end -->
```
If the block already exists, replace only what is between the markers; never duplicate it.

**Phase D — Build the context model for THIS project (always).** Before placing anything,
reason explicitly, as a context engineer, about this specific project using the model in the
spine. Do not apply a fixed rule: judge what the few things are that every task here needs (the
vision or goal, the load-bearing decisions, the core invariants) and that therefore justify
their permanent token cost in always-on context, versus what is detail that belongs in recall
leaves and only needs fetching when relevant. A tiny single-idea project can afford more
always-on; a sprawling codebase must push hard to leaves. State the resulting model in a
sentence or two: what you will keep always-on, what you will leave to recall, and why.

**Phase E — Migrate existing material (only if sources are given).** When $ARGUMENTS points at
existing notes (a `NOTES.md`, a `docs/` pile, a changelog, scattered `.md`):
1. **Inventory** the sources and read them.
2. **Propose a mapping** as a table: each chunk -> destination (a `journal/` / `knowledge/` /
   `canon/` leaf with its folder path, OR the spine for vision/rules, OR "leave out" with a
   reason). Apply Phase D: mark which items you recommend promoting to always-on (spine / canon
   / a note surfaced in an index) versus recall leaves, with the tradeoff stated. Flag
   duplicates and contradictions.
3. **Get approval** on the mapping and the folder taxonomy before writing anything.
4. **Execute through the writers**, each at its own gating: route journal items as in
   `/mem-log`, knowledge as in `/mem-note`, canon as in `/mem-canon` (advise-first,
   line-by-line; never bulk-write canon). Pull facts from the sources; never invent.
5. **Non-destructive:** leave originals in place unless I say move them. At the end, report what
   was migrated and where, and what you deliberately left out and why.
6. Run `/mem-index` on every store you touched.

**Always:** non-destructive; never overwrite a note or bulk-write canon; edit `CLAUDE.md` only
between the managed markers; report what existed, what you created, and what you placed in
recall versus always-on, each with absolute paths.
