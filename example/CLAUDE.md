# Example project

(A real project's own instructions would live here. The block below is what `/mem-init` adds and
manages — it is the memory spine, always loaded by the harness.)

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
