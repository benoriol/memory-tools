# important experiments (paper-critical subset)

The runs that anchor the paper: a pure projection of the experiment leaves flagged
`**Important:** yes`, same compact-pointer format as `experiments.md`. Always-read. To add or drop
a run here, flip that leaf's `**Important:**` flag and rerun `/mem-index experiments` — never
hand-edit between the markers.

<!-- mem-index: managed block; regenerate with /mem-index experiments. Do not hand-edit between the markers. -->

## 2026-06-05 — Gated adapter on GLUE

**Why:** first end-to-end test of the gated adapter against the matched LoRA baseline.
**Headline:** Gated adapter beats LoRA r=8 by +1.4 avg GLUE (85.5 vs 84.1) at equal trainable %.
→ [details](experiments/2026-06-05-gated-adapter-glue.md)

<!-- /mem-index -->
