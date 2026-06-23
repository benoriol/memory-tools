# 2026-06-01 — LoRA baseline on GLUE

**Why:** establish the parameter-efficient baseline our gated adapter must beat.
**Headline:** LoRA r=8 hits 84.1 avg GLUE at 0.30% trainable params.
**Important:** no
**Type:** training
**Setup:** stock LoRA (r=8, α=16) on all attention projections; RoBERTa-base; 3 seeds. Canonical
recipe otherwise (see `technical_notes/training-conventions.md`).

**Result:**

| method | trainable % | GLUE avg | MNLI | SST-2 | CoLA |
|---|---:|---:|---:|---:|---:|
| LoRA r=8 | 0.30 | 84.1 | 86.9 | 94.2 | 60.1 |

3-seed mean; scoring per `technical_notes/evaluation-protocol.md`.

**Paths:**
- Config: `configs/lora_r8_glue.yaml`
- Checkpoints: `runs/lora_r8/{mnli,sst2,cola,...}/seed-*/`
- Tracking: <https://tracker.example/runs/lora_r8_glue>

**Cross-references:** [gated adapter](2026-06-05-gated-adapter-glue.md)
