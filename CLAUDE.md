# memory-recall

Per-project multi-vector memory for Claude Code, exposed as an MCP
server with a visualization UI. See `README.md` for the user-facing
description and `DESIGN.md` for the architecture spec.

This file is the operator's quick-reference: how the memory tiers
compose, the conventions a Claude Code session should follow when
working in this repo, and the **Current project context** section
below — small, curated, must-know state that survives `/clear`.

---

## Current project context

Mutable. Holds the things you must know *right now* to be useful in
this repo. Updated deliberately when something material shifts —
not at every session boundary. Keep short (a few hundred tokens).

- **Shipped state**: commit `3d74346` replaced the old graph
  approach with `memory_recall` — multi-vector MCP, 5 tools,
  FastAPI+plotly viz, e25 benchmark family. Package is installed
  user-wide via `pipx install -e .`, so edits in `src/` go live
  immediately.
- **Active design work**: locking in the project-context tier. An
  earlier `SCRATCH.md` experiment was scrapped — regular
  conversation context already plays the scratchpad role; this
  section in CLAUDE.md is the replacement.
- **Bootstrap parity restored**: `memory-recall setup` (and
  `install-claude-md` / `uninstall-claude-md`) ported from the old
  `memory-graph` tooling. The CLAUDE.md operator-guidance template
  lives at `src/memory_recall/templates/claude_md_section.md`.
- **`memory_get` now batched**: signature is `memory_get(ids: list[str])`
  returning a list (None for misses) so multiple bodies can be
  fetched in a single MCP round-trip.
- **Known measurement gap**: sub-agent cost reporting in `e25b`
  prints $0.00. Need to plumb `ResultMessage.total_cost_usd`
  through `expand_for_capture` / `expand_for_search` before the
  Sonnet-vs-Haiku cost trade-off can be measured properly.
- **Replication owed**: single-run Sonnet-thinking-off recall@1
  swing (86% → 92% on 50 queries) is at the edge of noise. One
  more run would tighten the conclusion.
- **Triage owed**: untracked artifacts under
  `demos/eval/progressive/` and `demos/eval/results/` are
  pre-shipping exploration — decide whether to delete or move
  under `attic/`.

---

## Memory tiers — what goes where

| Tier | Where | When loaded | What goes in |
|------|-------|-------------|--------------|
| Rules + project context | `CLAUDE.md` (this file) | Every session, eagerly; re-read after `/clear` | Static guidance plus the curated "Current project context" section above. |
| Facts / preferences | Claude Code auto-memory at `~/.claude/projects/<dir>/memory/` | `MEMORY.md` index eagerly; entries on reference | Slowly-changing facts: user role, repo conventions, durable decisions, sub-agent config. |
| Long-term archive | `memory_recall` MCP (`.memory-recall/`) | Lazily, via `memory_retrieve_candidates` | Anything worth keeping permanently: bug write-ups, architectural decisions, knowledge from teammates. |

The tiers are deliberately distinct mechanisms. CLAUDE.md is plain
text the agent always sees. Auto-memory is markdown indexed via
`MEMORY.md`. `memory_recall` does multi-vector semantic retrieval
with sub-agent expansion at both capture and search time.

## Session protocol

At the **start** of every session:

1. Read the "Current project context" section above to orient.
2. Auto-memory's `MEMORY.md` index is already loaded — pull in
   linked entries if relevant.
3. Call `memory_status` if you expect to use `memory_recall` later
   (cheap; confirms the store is reachable).

**During** the session:

- For findings worth keeping permanently (architectural facts, bug
  root-causes, contracts with external systems): call
  `memory_capture(content)` to store them in long-term memory.
- For recall: prefer `memory_retrieve_candidates(query)` first;
  call `memory_get(ids=[...])` (batched) only for candidates whose
  summaries suggest the body has what you need.
- If a fact in auto-memory has become wrong, edit or delete the
  file under `~/.claude/projects/<dir>/memory/` and update
  `MEMORY.md` accordingly.

**Before stopping** (especially before context compaction):

- If something material shifted, update the "Current project
  context" section so the next cold-start has it.

## Bootstrapping memory-recall in a new project

The package is installed user-wide (`pipx install -e
/home/benet/code/memory-module-mcp`), so the `memory-recall` binary
is on PATH.

```bash
cd /path/to/project
memory-recall setup      # register + init + install-claude-md (idempotent)
memory-recall serve      # (Claude Code invokes this on demand)
```

Individual subcommands (`init`, `register`, `install-claude-md`,
`uninstall-claude-md`) can be run alone. `setup` accepts
`--skip-register / --skip-init / --skip-claude-md` and `--force`
(propagates to register + install-claude-md).

Optional visualization:

```bash
memory-recall viz        # http://localhost:8765
```

## Working on this repo

```bash
# Tests
.venv/bin/python -m pytest -q

# Real-model embedding test (slow; gated)
FASTEMBED=1 .venv/bin/python -m pytest tests/test_embed.py

# Run the recall-stress benchmark
cd demos/eval/experiments/e25_multivec_vs_singlevec
.venv/bin/python e25.py
```

Sub-agent default model is `claude-sonnet-4-6` with extended
thinking disabled (`thinking={"type": "disabled"}`). Don't change
this without re-running e25/e25b — the choice is empirical, not
arbitrary. Override per-call or via `MEMORY_RECALL_SUBAGENT_MODEL`.

## Repo layout reminder

```
src/memory_recall/
├── storage/        SQLite + markdown + ULIDs + Note model
├── embed/          Embedder protocol, FastEmbed, fake for tests
├── store.py        capture + multi-vector search
├── subagent.py     capture/search sub-agent (Sonnet, no thinking)
├── server.py       FastMCP server (5 tools)
├── cli.py          init / serve / status / viz / register / unregister
├── viz/            FastAPI + plotly viz
└── prompts/        capture.md, search.md

demos/eval/
├── experiments/    benchmarks (e10, e25, e25b, ...) + PLAN.md
└── lab/            exploratory scratch from earlier iterations (B1–B11)
```
