# experiments index

Full chronological record of every run (oldest first; recent at the tail). One compact pointer
per run; the detail leaf under `experiments/` is the source of truth. Regenerated from the leaves
by `/mem-index` — do not hand-edit between the markers.

<!-- mem-index: managed block; regenerate with /mem-index experiments. Do not hand-edit between the markers. -->

## 2026-06-01 — LoRA baseline on GLUE

**Why:** establish the parameter-efficient baseline our gated adapter must beat.
**Headline:** LoRA r=8 hits 84.1 avg GLUE at 0.30% trainable params.
→ [details](experiments/2026-06-01-lora-baseline-glue.md)

## 2026-06-05 — Gated adapter on GLUE

**Why:** first end-to-end test of the gated adapter against the matched LoRA baseline.
**Headline:** Gated adapter beats LoRA r=8 by +1.4 avg GLUE (85.5 vs 84.1) at equal trainable %.
→ [details](experiments/2026-06-05-gated-adapter-glue.md)

## 2026-06-09 — Gate-init ablation

**Why:** test whether the zero-init gate (training starts at the frozen model) is load-bearing or incidental.
**Headline:** Zero-init gate matters: random-init drops GLUE avg by 0.9 (85.5 -> 84.6).
→ [details](experiments/2026-06-09-gate-init-ablation.md)

<!-- /mem-index -->
