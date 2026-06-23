Scaffold a project's memory, wire the contract into CLAUDE.md, and optionally migrate existing notes. Optional args: a target notes root and/or existing sources to migrate (e.g. `./project_notes migrate docs/ NOTES.md`). $ARGUMENTS

Sets up the three-store layout the other `/mem-*` commands use, makes the always-read contract
live in `CLAUDE.md`, and (when pointed at existing material) reorganises that material into the
structure. Scaffolding is idempotent and non-destructive; migration is proposal-first and never
bulk-writes. There is no separate spine file: the always-on rules live in a managed block in
`CLAUDE.md` (which the harness always loads), and the per-store detail lives in the command files
and is read when you use them.

**Phase A — Scaffold (always).** Resolve the root: a path in $ARGUMENTS, else the `MEM_ROOT`
env var, else `./project_notes`. State the absolute path and what you will create before
creating it. Create if missing: the store folders `journal/`, `knowledge/`, `canon/`, and a
sibling index file for each — `journal.md`, `knowledge.md`, `canon.md` — that is just a one-line
header plus an empty managed block:
```
# journal index
<!-- mem-index: managed block; regenerate with /mem-index journal. Do not hand-edit between the markers. -->

<!-- /mem-index -->
```
Never overwrite an existing store, index, or note; report what already existed.

**Phase B — Wire the contract into CLAUDE.md (always).** In `./CLAUDE.md` (create if missing),
insert or refresh the managed block below, touching nothing outside the markers. This block is
the spine — the only always-on memory context — so keep it tight:
```
<!-- mem:begin (managed by memory-commands) -->
## Memory
Before substantive work, read the store indexes under project_notes/ (override the root with
MEM_ROOT): journal.md, knowledge.md, canon.md. Each index is the full tree plus a one-line
summary per note; the leaves hold the detail and are read on demand by following an index.

Stores and gating: journal/ (dated events; low gating; append-only) · knowledge/ (durable
methods, facts, gotchas; low to add, medium to edit) · canon/ (project story, decisions,
rationale; high gating, sentence-by-sentence approval). Capture with /mem-log, /mem-note,
/mem-canon, or /mem to route; run /mem-index after any write. Keep this always-on block lean:
only what is small, needed on most tasks, and costly to miss belongs here or in canon —
everything else is a leaf, one fetch away and surfaced by its index.

Notes are fallible: leaves are the source of truth; verify against the code, files, and results
when it matters, and raise any inconsistency you notice (a number that no longer matches, a
dangling link, a stale "results pending") on the spot with what and where, rather than silently
fixing it. The exhaustive sweep is /mem-audit.
<!-- mem:end -->
```
If the block already exists, replace only what is between the markers; never duplicate it.

**Phase C — Build the context model for THIS project (always).** Before placing anything, reason
explicitly, as a context engineer, about this specific project. The principle: the window is
finite and everything always-loaded (the CLAUDE.md block, the indexes) is paid on every task; the
indexes carry the full tree plus a one-line summary so the existence and gist of every leaf are
always known even when its body is not, which is what makes deferring to recall safe. Promote into
always-on context (the CLAUDE.md block or canon) only what is small, needed on most tasks, and
costly to miss (the vision, a core invariant, a load-bearing decision); make everything else a
leaf, where the only cost of leaving it out is one fetch. A tiny single-idea project can afford
more always-on; a sprawling codebase must push hard to leaves. State the resulting model in a
sentence or two: what you will keep always-on, what you will leave to recall, and why.

**Phase D — Migrate existing material (only if sources are given).** When $ARGUMENTS points at
existing notes (a `NOTES.md`, a `docs/` pile, a changelog, scattered `.md`):
1. **Inventory** the sources and read them.
2. **Propose a mapping** as a table: each chunk -> destination (a `journal/` / `knowledge/` /
   `canon/` leaf with its folder path, OR the CLAUDE.md block for vision/rules, OR "leave out"
   with a reason). Apply Phase C: mark which items you recommend promoting to always-on (the
   CLAUDE.md block / canon / a note surfaced in an index) versus recall leaves, with the tradeoff
   stated. Flag duplicates and contradictions.
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
