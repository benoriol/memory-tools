# 2026-06-05 — Gated adapter on GLUE

**Why:** first end-to-end test of the gated adapter against the matched LoRA baseline.
**Headline:** Gated adapter beats LoRA r=8 by +1.4 avg GLUE (85.5 vs 84.1) at equal trainable %.
**Important:** yes
**Type:** training
**Setup:** gated adapter (per-layer scalar gate, zero-init so training starts at the frozen
model) in place of LoRA; same r=8 budget, same RoBERTa-base, same 3 seeds. Only the adapter block
differs from the baseline recipe.

**Result:**

| method | trainable % | GLUE avg | MNLI | SST-2 | CoLA |
|---|---:|---:|---:|---:|---:|
| LoRA r=8 (baseline) | 0.30 | 84.1 | 86.9 | 94.2 | 60.1 |
| **gated adapter** | 0.30 | **85.5** | 87.4 | 94.8 | 64.0 |

Largest gain on CoLA (+3.9). p<0.01 paired over seeds × tasks.

**Paths:**
- Config: `configs/gated_adapter_glue.yaml`
- Checkpoints: `runs/gated_adapter/{mnli,sst2,cola,...}/seed-*/`
- Tracking: <https://tracker.example/runs/gated_adapter_glue>

**Cross-references:** [LoRA baseline](2026-06-01-lora-baseline-glue.md) ·
[gate-init ablation](2026-06-09-gate-init-ablation.md)
