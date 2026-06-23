# Training conventions

**Summary:** canonical recipe shared by all runs: RoBERTa-base, AdamW, fixed schedule, pinned seeds.

- Backbone: RoBERTa-base, frozen except the adapter/LoRA params.
- Optimizer: AdamW, lr 4e-4 (adapter params), linear warmup 6%, cosine decay, batch 32, 10 epochs.
- Seeds: {0, 1, 2}; set Python/NumPy/torch + `cudnn.deterministic=True`.
- Only document **deltas** from this recipe in an experiment's `**Setup:**` field; do not restate
  the whole recipe per run.
- This is on-demand depth, not an always-on rule. Hard guardrails (hardware pinning, never
  overwrite a checkpoint dir) belong in `CLAUDE.md`, not here.
