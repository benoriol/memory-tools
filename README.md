# memory-recall

Per-project multi-vector memory for Claude Code, exposed as an MCP
server with a visualization UI.

Notes are stored as markdown files with YAML frontmatter; a SQLite
index plus locally-computed embeddings (FastEmbed,
sentence-transformers/all-MiniLM-L6-v2) power the retrieval. Each
note is indexed under several embedded "views" — its summary, plus
sub-agent-generated keywords and paraphrases — so a query that uses
different vocabulary than the original note can still find it.

## The API choice that matters: two-step recall

The main agent recalls memories in two cheap steps:

1. **`memory_retrieve_candidates(query)`** — open-ended input (a
   question, a task, a bug, an error message). A sub-agent expands
   it into canonical keywords and paraphrases, and you get back the
   top-k candidate notes with their **summaries only**. Typical
   response is ~1000 tokens for k=10.
2. **`memory_get(id)`** — for whichever candidate(s) the main agent
   judges relevant, fetch the full body.

Most calls only need step 1. Bodies are only loaded when actually
needed, and the main agent — not the memory layer — decides what's
relevant.

## Five tools

| Tool | Purpose |
|------|---------|
| `memory_capture(content, tags?)` | Save an open-ended raw note; sub-agent indexes it under summary + keywords + paraphrases. |
| `memory_retrieve_candidates(query, k=10)` | **Step 1 of recall.** Top-k candidates with summaries. |
| `memory_get(id)` | **Step 2 of recall.** Full body of one note. |
| `memory_list(limit=100, offset=0)` | Browse all notes, newest first. |
| `memory_status()` | Store stats. |

## Install

```bash
pipx install -e .
```

Then in any project directory:

```bash
memory-recall init       # creates .memory-recall/
memory-recall register   # writes .mcp.json so Claude Code picks it up
memory-recall serve      # (Claude Code runs this for you when needed)
```

## Visualization

```bash
memory-recall viz        # http://localhost:8765 by default
```

Browse all notes, see a 2D PCA projection of their embeddings, and
test searches interactively — the UI shows what keywords/paraphrases
the sub-agent generated for the query alongside the ranked results.

## Sub-agent configuration

The capture and recall expansions are done by a `claude_agent_sdk`
sub-agent. Defaults (measured choice — see `DESIGN.md` and
`demos/eval/experiments/e25_*`):

- Model: `claude-sonnet-4-6`
- Extended thinking: explicitly **disabled**
  (`thinking={"type": "disabled"}`)
- Override via env var: `MEMORY_RECALL_SUBAGENT_MODEL`

## Architecture

```
Claude Code
  └── main agent
        ├── memory_capture          ─┐
        ├── memory_retrieve_candidates ─┤
        ├── memory_get              ─┤  MCP tools
        ├── memory_list             ─┤
        └── memory_status           ─┘
              │
              ▼
        memory-recall MCP server (stdio)
              ├── Sub-agent (Sonnet 4.6, no thinking) — expands raw
              │   text into title + summary + keywords + paraphrases
              ├── Local embedder (FastEmbed MiniLM) — one vector
              │   per view
              └── SQLite store + markdown files at .memory-recall/
```

## Repository layout

```
src/memory_recall/
  storage/       SQLite + markdown + ULIDs + Note model
  embed/         Embedder protocol, FastEmbed, fake for tests
  store.py       capture + multi-vector search + max-pool ranking
  subagent.py    capture/search sub-agent (Sonnet, no thinking)
  server.py      FastMCP server registering the 5 tools
  cli.py         init / serve / status / viz / register / unregister
  viz/           FastAPI + plotly visualization
  prompts/       capture.md, search.md
tests/           pytest suite
demos/eval/
  experiments/   benchmarks (e10, e25, e25b, ...) with READMEs
  lab/           exploratory scratch from earlier iterations
```

See `DESIGN.md` for the schema, the multi-vector retrieval algorithm,
and the rationale behind the API choices.

See `demos/eval/experiments/PLAN.md` for the research questions this
package is being evaluated against, and per-experiment READMEs for
results.
