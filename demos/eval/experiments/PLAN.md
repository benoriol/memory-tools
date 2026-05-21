# Research plan: when and how does memory help?

We are studying **memory in general** — how the *structure and use* of
written-down knowledge across sessions affects an LLM agent's
accuracy, cost, and speed. We are **not** validating any specific
memory implementation. In particular, the `memory-graph` MCP server in
this repo is set aside until the simple questions are answered with
simpler tools.

## Underlying questions (from `lab/QUESTIONS.md`)

- **Q1**: Does memory help at all?
- **Q2**: What is the best storage shape? — single file vs many
  isolated files vs files with explicit relations.
- **Q3**: Does abstraction-layered structure help? — coarse summaries
  for context, fine detail for what matters right now.
- **Q4**: Does graph-structured memory beat flat multi-note memory?

## Implementation philosophy

Every memory variant is implemented using the agent's existing
**Read / Write / Bash / Glob / Grep** tools. The structure is defined
*entirely in the prompt* — "your notes live in directory X with
convention Y; to recall, do Z." No MCP server, no custom tooling, no
embeddings. The agent does the storage and the retrieval itself.

This keeps the comparison about *the memory's structural design*, not
about any particular tool's ergonomics. If a structure helps when the
agent has to implement it manually, the finding is robust; we can
later add a tool to make it cheaper.

## Memory variants studied

| ID | Name | What the prompt instructs |
|----|------|---------------------------|
| **NONE** | no notes | Don't write anything down; just answer when asked. |
| **SINGLE** | one flat file | Maintain `NOTES.md` — append a section per finding; read the whole file to recall. |
| **MULTI** | many files, flat | Write each finding to `notes/<slug>.md`; recall via `ls notes/` + `grep` + `Read`. |
| **LINKED** | many files + cross-refs | Same as MULTI, but each note has a `## Related` section listing other note filenames. Follow links during recall. |
| **HIER** | hierarchical summaries + details | `notes/summary/<topic>.md` (short, one paragraph) + `notes/detail/<slug>.md` (full). Recall reads summaries first, then drills into details when needed. |

These are the abstract storage shapes the experiments compare. Future
experiments may add variants (e.g. a tag-index file, an embedding cache,
a deduplication pass) but they should justify themselves against this
ladder.

## Realism ground rules

1. **Files stay on disk** between sessions — memory must compete with
   what could be re-derived.
2. **No tools removed** from the baseline. NONE has Read/Write/Bash
   like everyone else; it just isn't *told* to write notes.
3. **Each session is a fresh `query()` call** — only state that
   persists is what's on disk.
4. **System limits**: 32GB RAM, 64 cores, no GPU.

## Metrics, every experiment

- **Accuracy** (task-specific).
- **Cost** (`total_cost_usd`).
- **Tokens** (input, output, cache_read, cache_creation).
- **Wall time** per phase.
- **Tool-call profile** (which tools, how many calls).

## Reflection loop

After every run, write a `## Reflection` section in the experiment's
README covering:

1. What we expected.
2. What we observed (numbers + tool-call profile + inspection of the
   actual notes the agent wrote).
3. Why (mechanism, not headline).
4. Implications for the next experiment.

Then either proceed to the next planned experiment or adapt one. New
experiments get appended with the next available number; the index in
`README.md` is authoritative.

---

## Phase 1 — Q1: does memory help at all?

### e10. NONE vs SINGLE on cross-session bug recall
The most basic question, asked simply. Bug-investigation task (the
e01 corpus is fine to reuse — 30 buggy modules). Two arms:

- **NONE**: phase-1 prompt says "investigate this codebase". Phase-2
  prompt asks 30 diagnostic questions and tells the agent the prior
  session left no notes.
- **SINGLE**: phase-1 prompt says "investigate and maintain
  `NOTES.md`". Phase-2 prompt says "your prior session's notes are in
  `NOTES.md`; consult it before re-reading source."

Both arms have Write/Edit/Bash/Glob/Grep/Read. Files stay on disk
between phases.

**Pass**: SINGLE's phase-2 cost ≤ 0.5 × NONE's phase-2 cost, both
arms ≥ 28/30 accuracy.

**Why this isn't a duplicate of e01**: e01 conflated several things.
This is the cleanest possible test of Q1: same task, same baseline
tools, the only difference is whether the prompt instructs the agent
to leave notes.

---

## Phase 2 — Q2: storage shape

### e20. SINGLE vs MULTI on the same task
Does breaking the flat file into many files change anything? Same
task as e10. Two arms differ only in prompt convention:

- **SINGLE**: as in e10.
- **MULTI**: phase-1 says "for each bug, write
  `notes/module_NN.md`"; phase-2 says "your notes are in `notes/`;
  use `ls notes/` and read individually."

**Pass**: MULTI's phase-2 cost ≤ 0.7 × SINGLE's phase-2 cost. (Or
the opposite — if SINGLE wins on this task, that's also a finding.)

We expect MULTI to win when phase-2 questions are paraphrased enough
that the agent only needs one note per question. We expect SINGLE to
tie or win when most questions need the whole picture.

---

## Phase 3 — Q4: do explicit links help?

### e30. MULTI vs LINKED on chained queries
First experiment where we deliberately design questions that require
**traversing relationships**. Same 30-module corpus, but the bugs are
woven into a dependency graph (module_07 imports module_12; module_12
calls into module_19). Phase-2 questions ask "if module_07's bug
fires, which other modules' behavior is affected?" — multi-hop.

- **MULTI**: notes are independent; agent must grep/search to find
  the chain.
- **LINKED**: each note has a `## Related` section listing dependent
  notes; agent can follow links.

**Pass**: LINKED ≥ MULTI accuracy − 0 *and* LINKED's phase-2 cost ≤
0.7 × MULTI's phase-2 cost. (Or LINKED wins on accuracy by ≥15 pp.)

If LINKED doesn't win here, explicit cross-references aren't earning
their keep even on tasks that should reward them.

---

## Phase 4 — Q3: do abstraction layers help?

### e40. MULTI vs HIER under context pressure
Harder corpus: 100 modules grouped into 10 subsystems. Phase-2
questions need *both* one module's specific detail and awareness of
its subsystem's role.

- **MULTI**: flat notes, one per module.
- **HIER**: summary notes per subsystem (`notes/summary/`) + detail
  notes per module (`notes/detail/`). Prompt instructs: "read all
  relevant summaries first; only drill into details for the modules
  in question."

To make the abstraction matter, we'll measure under a deliberate
**token budget** for retrieval (capped via the phase-2 prompt: "load
at most 4K tokens of notes total before answering"). Without a
budget, MULTI can just load everything; with one, it has to choose.

**Pass**: HIER beats MULTI on accuracy under the same token budget,
by ≥10 pp.

---

## Phase 5 — generalization / optimization

### e50. Cheaper model variant
Run the e10 winner (likely SINGLE) and the e20/e30 winners with the
**main agent set to Haiku 4.5** for phase 1 and 2. Does the structure
that wins with Sonnet still win with Haiku, or does Haiku's smaller
reasoning capacity favor a different shape (e.g. it relies more on
SINGLE because it can't navigate MULTI as efficiently)?

### e60. Amortization curve
Vary phase-2 query count ∈ {10, 30, 100, 300} on the e10-winner
configuration. Identify the break-even point — at how many queries
does memory's phase-1 capture cost actually pay back?

---

## Stop conditions

- If **e10** shows NONE ≈ SINGLE on cost: the whole memory premise is
  weak on this task; redesign the task before more experiments.
- If **e20** shows SINGLE ≥ MULTI clearly: there's no point pursuing
  more elaborate shapes; the simplest works.
- If **e30** and **e40** both fail to beat their flat baselines:
  structural memory (links, hierarchy) is not contributing — Q2
  answered with "simplest wins"; Q3/Q4 answered "no".

## Order of operations

1. **e10** first — cheapest, most fundamental.
2. **e20** if e10 passes.
3. **e30** and **e40** can run in parallel after e20 (they don't
   depend on each other).
4. **e50** and **e60** last.

## Status of pre-pivot experiments

- `e01_realistic_baseline/` and `e01b_explicit_schema/` used the
  memory-graph MCP. They are **superseded** by this plan but kept on
  disk as a record of the MCP-ergonomics finding (`content` vs `body`
  field, ToolSearch overhead).
- `e02`–`e06` empty stubs from the previous draft are **superseded**
  by `e10`–`e60` above. Their folders may be removed or repurposed.

## What this plan still does NOT cover

- Multi-agent / shared memory.
- Long-horizon decay and pruning.
- Tasks that aren't Q&A (iterative coding, debugging, design work).
- Adversarial / contradictory memory injection.
- The memory-graph MCP specifically (deferred until simple
  questions are answered).
