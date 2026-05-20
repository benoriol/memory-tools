# memory-graph-mcp

Per-project graph memory for Claude Code, exposed as an MCP server.

Notes are stored as markdown files with YAML frontmatter; a SQLite
index provides fast lookups and embedding-based semantic search. The
model is deliberately flat: every note is the same kind of thing with
a free-text `kind` label (e.g. `experiment`, `mistake`, `user_said`,
`bug_fix`, `principle`) that's purely descriptive. Three edge types
do the structural work — `abstracts` (directed: from-node is more
abstract than to-node), `related` (lateral), and `supersedes` (the
only behavior-bearing edge — flips the old note's status).

## How it works

The main agent in Claude Code calls three tools:

| Tool                         | When                                         |
| ---------------------------- | -------------------------------------------- |
| `memory_remember(dump)`      | After experiments / decisions / lessons      |
| `memory_retrieve(query)`     | Before non-trivial decisions, design choices |
| `memory_compact(scope?)`     | When a region of the graph needs cleanup     |

Each one spawns a **memory sub-agent** (via the Claude Agent SDK,
in-process) that has access to the graph primitives. The sub-agent
decomposes dumps into multiple notes at appropriate abstraction
levels, walks the graph to find connections, and returns a short
synthesis. Exploration tokens stay in the sub-agent; the main agent
only sees the result.

Ten lower-level primitives are also exposed for direct use:
`memory_search`, `memory_get`, `memory_neighbors`, `memory_capture`,
`memory_capture_batch`, `memory_link`, `memory_unlink`,
`memory_supersede`, `memory_mark`, `memory_status`.

## Architecture

```
Claude Code (Max subscription)
  └── main agent calls memory_remember / retrieve / compact
        │
        ▼
  memory-graph MCP server (stdio)
    ├── primitives: search / get / neighbors / capture / link / ...
    └── orchestration: spawns Agent SDK sub-agent in-process,
                       using CLAUDE_CODE_OAUTH_TOKEN to auth against
                       the user's subscription.
                       Sub-agent's tools are also the primitives
                       above, surfaced via create_sdk_mcp_server.
        │
        ▼
  .memory-graph/  (per-project, in the repo root)
    ├── notes/*.md     <- markdown with YAML frontmatter
    ├── index.db       <- SQLite + embeddings (derivable from notes/)
    ├── _operator/     <- sub-agent's working notes
    └── _pending/      <- deferred items
```

No API key needed; runs entirely on a Claude Max subscription via the
Agent SDK's OAuth-token authentication. Embeddings are local
(FastEmbed `all-MiniLM-L6-v2`, ~80 MB on disk).

## Install

See [`docs/INSTALL.md`](./docs/INSTALL.md). Roughly:

```bash
claude setup-token              # one-time
pipx install -e .               # install the package
# add MCP server entry to ~/.claude.json with CLAUDE_CODE_OAUTH_TOKEN
cd ~/projects/your-project
memory-graph init               # creates .memory-graph/
# paste docs/CLAUDE.md.template into your project's CLAUDE.md
```

## Status

V0. Working pieces:

- [x] SQLite + markdown storage with typed edges, ULID ids
- [x] Local FastEmbed embeddings
- [x] 10 pure primitives (search, get, neighbors, capture, link, ...)
- [x] MCP server exposing all primitives over stdio
- [x] Agent SDK orchestration: remember / retrieve / compact
- [x] CLI: init / serve / digest / reindex / status
- [x] CLAUDE.md template and install docs
- [x] 73 unit tests passing

Not yet:

- [ ] Auto-update of operator-context after each operation
- [ ] Tiered consolidation (continuous → per-insert → regional → global)
- [ ] PreToolUse hook for "recall before risky edits"
- [ ] Confidence decay and `last_verified_at` re-stamping
- [ ] Path-anchored archaeology surfacing
- [ ] Pending-op resume for clarification round-trips
- [ ] sqlite-vec swap when stores get big

## Layout

```
src/memory_graph/
├── storage/        SQLite + markdown + Note model + ULID ids
├── embed/          Embedder protocol, FastEmbed, deterministic fake
├── primitives/     Store class with all memory operations
├── orchestration/  Agent SDK runner + remember / retrieve / compact
├── prompts/        system.md + remember.md + retrieve.md + compact.md
├── server.py       FastMCP server registering 13 tools
└── cli.py          memory-graph: init / serve / digest / reindex / status

tests/              Pytest suite, ~75 tests
docs/               INSTALL.md, CLAUDE.md.template
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

Two opt-in slow tests:

- `FASTEMBED=1 pytest -k local_embedder_real_model` — downloads
  ~80 MB on first run, verifies the real model loads.
- `CLAUDE_CODE_OAUTH_TOKEN=... pytest -k end_to_end` — runs the
  real sub-agent against the Anthropic API.
