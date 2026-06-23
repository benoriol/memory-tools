# 2026-06-09 — Gate-init ablation

**Why:** test whether the zero-init gate (training starts at the frozen model) is load-bearing or
incidental.
**Headline:** Zero-init gate matters: random-init drops GLUE avg by 0.9 (85.5 -> 84.6).
**Important:** no
**Type:** training
**Setup:** the gated-adapter recipe from 2026-06-05, varying only the gate initialization
(zero-init vs N(0,0.02) random-init). Same budget, seeds, tasks.

**Result:**

| gate init | GLUE avg | CoLA |
|---|---:|---:|
| zero (canonical) | 85.5 | 64.0 |
| random N(0,0.02) | 84.6 | 61.2 |

Random-init removes most of the CoLA gain over LoRA, confirming the "start at the frozen model"
property is what helps the low-resource tasks.

**Paths:**
- Config: `configs/gated_adapter_glue.yaml` with `--gate-init {zero,random}`
- Tracking: <https://tracker.example/runs/gate_init_ablation>

**Cross-references:** [gated adapter](2026-06-05-gated-adapter-glue.md)
