# Gated Adapter (example research project)

(A real project's own instructions — environment, hardware pinning, commit policy — would live
here. The block below is what `/mem-init` adds and manages: the memory spine, always loaded by
the harness.)

<!-- mem:begin (managed by memory-commands) -->
## Memory (paper notes)
Before substantive work, read these always-on indexes under project_notes/ (override the root
with MEM_ROOT): technical_notes.md, paper_narrative.md, and experiments_important.md (the
paper-critical run subset). The full run history is experiments.md (on-demand) with detail leaves
under experiments/ — open them when you need a specific run rather than reasoning from the
narrative's summaries.

Destinations and gating: experiments/ + experiments.md (dated run leaves; new leaf = suggest,
then approval; existing leaf = keep current yourself) ·
experiments_important.md (the paper-critical subset; a projection of each leaf's **Important:**
yes|no flag, rebuilt by /mem-index, never hand-edited) · technical_notes/ (durable
methodology/gotchas; low to add, medium to edit) · paper_narrative.md (the curated paper argument;
high, sentence-by-sentence approval). Capture with /mem-log, /mem-note, /mem-canon, or /mem to
route; run /mem-index after any write. Keep the always-on set lean: only paper-critical runs
earn the important subset; everything else stays one fetch away in experiments.md.

Your responsibilities, without being told:
- Suggest a new experiment leaf whenever a run or result is worth recording; write it only after
  I approve.
- Keep existing experiment leaves current: as runs progress, finish, or change (new numbers,
  paths, reruns, fixes, extra information), update the leaf's Result, Headline, Paths, and status
  yourself, then run /mem-index. Do not wait to be asked; stale "results pending" is your bug.
  Never delete recorded history, and never flip **Important:** without my say-so.
- Do not oversplit: one leaf per experiment. Reruns, extra seeds, new evals, follow-up numbers,
  and fixes to the same experiment go into its existing leaf; propose a new leaf only for a
  genuinely different experiment (new question, method, or setting).
- Look up relevant experiments and technical notes yourself before and during work, by following
  the indexes. Take them with a pinch of salt, older ones especially: the project moves fast and
  notes go stale, so check them against the current code, configs, and results.

Notes are fallible: detail leaves are the source of truth; verify against them and raise any
inconsistency you notice (a narrative number that no longer matches its leaf, a dangling link, a
stale "results pending", an important entry not flagged on its leaf) on the spot with what and
where, rather than silently fixing it. The exhaustive sweep is /mem-audit.
<!-- mem:end -->
