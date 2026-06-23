# Gated Adapter — paper narrative

Map of the paper: the argument and the evidence behind it. **Source of truth:** per-run facts ->
the detail leaves under `experiments/`; this file is canonical only for the *synthesis* (the
story, cross-run tables, which claim each result backs). Maintained via `/papernote`
(sentence-gated) — never auto-written. Methodology lives in `technical_notes/`.

## TL;DR (abstract)
- A per-layer **gated adapter**, zero-initialized so fine-tuning starts exactly at the frozen
  model, matches the LoRA budget but adapts more gracefully on low-resource tasks.
- At equal trainable %, it beats LoRA on GLUE, with the gain concentrated where data is scarce.

## Method
- **Gated adapter** = adapter block + a per-layer scalar gate, zero-init.
  exp [2026-06-05](experiments/2026-06-05-gated-adapter-glue.md) · the zero-init "start at the
  frozen model" property is the load-bearing piece (ablation below).

## Main results
- **Beats the matched LoRA baseline** at equal trainable %: GLUE avg 85.5 vs 84.1 (+1.4), largest
  on CoLA (+3.9), p<0.01. → [2026-06-05](experiments/2026-06-05-gated-adapter-glue.md) vs the
  baseline [2026-06-01](experiments/2026-06-01-lora-baseline-glue.md).

## Ablations
- **Zero-init gate is load-bearing** — random-init drops GLUE avg 0.9 and removes most of the CoLA
  gain. → [2026-06-09](experiments/2026-06-09-gate-init-ablation.md)

## Supplementary
- (none yet)

## Open / pending
- Scale beyond RoBERTa-base; larger-budget (r=16/32) sweep not run.
- Test split is dev-set only; no GLUE leaderboard submission.
