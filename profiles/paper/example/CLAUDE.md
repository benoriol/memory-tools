# Gated Adapter (example research project)

(A real project's own instructions — environment, hardware pinning, commit policy — would live
here. The block below is what `/paper-init` adds and manages: the memory spine, always loaded by
the harness.)

<!-- mem:begin (managed by memory-commands) -->
## Memory (paper notes)
Before substantive work, read these always-on indexes under project_notes/ (override the root
with MEM_ROOT): technical_notes.md, paper_narrative.md, and experiments_important.md (the
paper-critical run subset). The full run history is experiments.md (on-demand) with detail leaves
under experiments/ — open them when you need a specific run rather than reasoning from the
narrative's summaries.

Destinations and gating: experiments/ + experiments.md (dated run leaves; low; append-only) ·
experiments_important.md (the paper-critical subset; a projection of each leaf's **Important:**
yes|no flag, rebuilt by /paper-index, never hand-edited) · technical_notes/ (durable
methodology/gotchas; low to add, medium to edit) · paper_narrative.md (the curated paper argument;
high, sentence-by-sentence approval). Capture with /logexp, /technote, /papernote, or /note to
route; run /paper-index after any write. Keep the always-on set lean: only paper-critical runs
earn the important subset; everything else stays one fetch away in experiments.md.

Notes are fallible: detail leaves are the source of truth; verify against them and raise any
inconsistency you notice (a narrative number that no longer matches its leaf, a dangling link, a
stale "results pending", an important entry not flagged on its leaf) on the spot with what and
where, rather than silently fixing it. The exhaustive sweep is /paper-audit.
<!-- mem:end -->
