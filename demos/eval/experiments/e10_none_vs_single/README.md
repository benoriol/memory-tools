# e10 — NONE vs SINGLE on cross-session bug recall

**Question:** Q1 — does writing notes at all help, when the task spans
a session boundary?

## Hypothesis

When the phase-2 agent has no in-context history of phase 1 but the
source files are still on disk, the SINGLE arm (which leaves a
`NOTES.md` summary) reaches phase-2 conclusions far more cheaply than
the NONE arm (which must re-investigate from scratch).

Specifically: SINGLE's phase-2 cost ≤ 0.5 × NONE's phase-2 cost, both
arms ≥ 28/30 accuracy.

## Design

Same corpus as e01 — 30 small Python modules, one planted bug per
module, bug ground-truth held in the test harness (not on disk). See
`../e01_realistic_baseline/e01.py` for the bug catalog; we reuse
BUG_SPECS verbatim.

Two arms differ **only by prompt convention**:

### Arm NONE
- **Phase 1 prompt:** "Investigate this codebase. Identify every
  defect." Does NOT mention notes; the agent is free to write notes
  if it chooses, but is not instructed to.
- **Phase 2 prompt:** "Answer these diagnostic questions. The prior
  session did not leave you any notes. You'll need to read the
  source yourself."

### Arm SINGLE
- **Phase 1 prompt:** "Investigate this codebase. Maintain a
  `NOTES.md` file as your only persistent record — append one section
  per module with the bug type and one-line explanation."
- **Phase 2 prompt:** "Answer these diagnostic questions. Your prior
  session left you `NOTES.md` — read it once and use it; only read
  source modules if your notes are unclear."

Both arms have **identical tools**: Read, Bash, Glob, Grep, Write,
Edit. No MCP. Files persist between phases.

Each phase is a fresh `query()` call (no in-context carry-over).

## Metrics

- Accuracy: hits / 30 (module name + bug-keyword match, same grader as
  e01).
- Phase 1 cost, phase 2 cost.
- Phase 1 time, phase 2 time.
- Tokens (input/output/cache).
- Tool-call profile per phase.
- **For NONE**: did the agent voluntarily write any files in phase 1?
  (If yes, this becomes interesting — see "Open dynamics" below.)
- **For SINGLE**: size of NOTES.md after phase 1.

## Pass criterion (pre-declared)

- Both arms ≥ 28/30.
- SINGLE phase-2 cost ≤ 0.5 × NONE phase-2 cost.

Failure on the cost criterion = a real finding: "even single-file
notes don't pay back at this corpus size." Failure on the accuracy
criterion for SINGLE = the agent's notes were insufficient.

## Open dynamics to inspect

The agent in NONE may *spontaneously* write a notes file in phase 1
without being told to (the e01 no_memory arm did this). If so, NONE
isn't really NONE. Inspect what the NONE agent wrote; if it left
notes, the comparison is contaminated and we'll need to either tell
NONE explicitly "don't write notes" or rename the arm to
"unprompted-notes" and design a stricter NONE.

## How to run

```bash
cd demos/eval/experiments/e10_none_vs_single
python e10.py 2>&1 | tee run.log
```

Expected runtime: ~3-5 minutes.

## Result (2026-05-21)

| | NONE | SINGLE |
|---|---|---|
| Accuracy | **30 / 30** | **30 / 30** |
| Phase 1 cost | $0.114 | $0.194 (+70%) |
| Phase 2 cost | **$0.127** | **$0.072 (−43%)** |
| Phase 1 time | 89s | 98s |
| Phase 2 time | 69s | 44s |
| Total cost | $0.241 | $0.266 (+10%) |
| Phase 1 scratch files | **0** | NOTES.md (8.3 KB) |
| Phase 1 tool calls | Bash×6 | Agent×1, Bash×1, Read×30, Write×1 |
| Phase 2 tool calls | Agent×1, Bash×1, Read×30 | Read×3, Bash×1 |

**Verdict: FAIL (pass criterion), but nuanced.** SINGLE phase-2 cost
was 56% of NONE phase-2 cost — close to but not under the
pre-declared 50% threshold. Worth interpreting carefully (see below).

## Reflection

### What we expected
SINGLE's notes would let phase 2 skip re-reading the source, dropping
phase-2 cost to ≤50% of NONE.

### What we observed
- **Phase 2 ratio: 0.564** (≤ 0.5 declared pass) — fails the strict
  threshold but the *mechanism* is exactly what we predicted. NONE
  re-read all 30 modules in phase 2 (Read×30); SINGLE read NOTES.md
  + 2 source files (Read×3). The memory clearly worked.
- **Phase 1 was +70% more expensive with SINGLE.** Writing NOTES.md
  was real overhead: the agent had to organize findings, draft the
  file, and serialize it. NONE didn't have to do any of that — it
  read modules, formed a mental model, and moved on (Bash×6 only).
- **Net total cost: SINGLE was 10% MORE expensive than NONE.** On a
  single follow-up session, memory loses on dollars.
- The NONE arm did NOT spontaneously write notes — clean comparison,
  no contamination from e01's "agent writes a markdown file anyway"
  problem. The clearer phase-1 prompt (no mention of notes) was
  enough to suppress that behavior.

### Why memory still helps despite the verdict
The headline "SINGLE costs 10% more" hides the actual finding:

- **Phase 1 capture is a fixed cost** — paid once.
- **Phase 2 retrieval savings scale with the number of phase-2
  queries** — paid every time you come back.

Break-even is roughly when the phase-2 *savings* exceed the phase-1
*premium*. Here:

- Phase-1 premium: $0.080 ($0.194 − $0.114).
- Phase-2 saving per session: $0.055 ($0.127 − $0.072).

So memory pays back **after ~1.5 follow-up sessions**. For ≥2 follow-ups
on this corpus, memory wins on total cost. For exactly one follow-up,
memory loses by 10%.

This is the right framing for Q1 — not "does memory help yes/no" but
"under what amortization does memory help?"

### What this implies for the next experiments
1. **The pass criterion was too aggressive.** The strict "phase-2 ≤
   0.5×" rule treats a single follow-up as the relevant case. The
   real lever is the number of follow-up sessions. Future
   experiments should report phase-1 and phase-2 cost separately and
   compute break-even.
2. **e20 (SINGLE vs MULTI) needs to be rethought slightly.** MULTI
   will likely have *higher* phase-1 cost (30 Write calls vs 1) and
   uncertain phase-2 behavior. On this task (30 questions / 30
   modules / 1:1 mapping), MULTI probably has no path to win —
   either it reads all 30 files (worse than NONE) or it reads
   one-per-question (still many reads). MULTI's case for winning
   needs a task with **many notes but few relevant per query** —
   that's what we should build into e20's task design.
3. **e60 (amortization curve) becomes more important** because it
   directly measures the break-even point implied here. Could
   reasonably be promoted earlier in the order.

### Next move
Run **e20** with two changes from the original spec:

- Report phase-1 and phase-2 separately; compute break-even.
- Use a task where **MULTI's selective retrieval can plausibly pay
  off** — e.g. a corpus of 100 notes but only ~3 relevant per
  question. This is closer to a real-world memory workload.

Drafting e20 next.
