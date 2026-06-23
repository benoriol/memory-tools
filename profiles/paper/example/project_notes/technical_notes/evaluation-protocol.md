# Evaluation protocol

**Summary:** how GLUE runs are scored: 3 seeds, dev-set, mean of per-task metrics, CoLA in MCC.

- 3 seeds per (method, task); report the mean. Spread is small (<0.3 avg) but always state seeds.
- Dev-set scores (test labels are not public). "GLUE avg" = unweighted mean over the 8 tasks.
- Per-task metric: accuracy, except CoLA (Matthews corr) and STS-B (Spearman). MNLI = mean of
  matched/mismatched.
- Trainable % = trainable params / total backbone params, reported to 2 decimals.
- Significance: paired test over (seed × task) pairs vs the matched baseline; report p.
