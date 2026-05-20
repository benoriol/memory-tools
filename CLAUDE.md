# memory-graph-mcp

Per-project graph memory for Claude Code. Notes are markdown +
YAML frontmatter; SQLite is a derived index; sub-agents spawned via
the Agent SDK do the smart work; the main agent calls three tools
(`memory_remember`, `memory_retrieve`, `memory_compact`) plus 10
lower-level primitives.

Read `README.md` for architecture and `docs/INSTALL.md` for the full
walkthrough. This file is the operator's quick-reference for working
on this repo and bootstrapping the tool into other projects.

---

## How to bootstrap the memory module in a new project

You only need this once per project. The package is already installed
user-wide (via `pipx install -e .` against this repo), so the
`memory-graph` binary is on PATH.

### Prerequisites (one-time, machine-wide)

```bash
# 1. Claude Code OAuth token — required for remember/retrieve/compact
#    (the 10 primitives work without it; only the agentic tools need auth)
claude setup-token
# paste the token into ~/.bashrc:
echo 'export CLAUDE_CODE_OAUTH_TOKEN=<paste>' >> ~/.bashrc
source ~/.bashrc

# 2. (If not already done) Install this package so the CLI is on PATH
pipx install -e /home/benet/code/memory-module-mcp
# Verify:
which memory-graph

# If you pipx-installed before 2026-05-19, claude-agent-sdk was an
# optional extra and is now required. Inject it once:
pipx inject memory-graph-mcp claude-agent-sdk
# (or simply: pipx reinstall memory-graph-mcp)
```

### Per new project — one command

```bash
cd /path/to/the/new/project

# One-shot: register MCP + init store + install CLAUDE.md protocol
memory-graph setup
#   Idempotent. Re-runs are safe — each step reports "already done"
#   and continues. Pass --force to replace an existing .mcp.json entry
#   or a stale CLAUDE.md section. --skip-register / --skip-init /
#   --skip-claude-md to do only some of the steps.

# (Optional) Stop-hook for auto-digest at session end
mkdir -p .claude
cat > .claude/settings.json <<'EOF'
{
  "hooks": {
    "Stop": [
      { "command": "memory-graph digest --transcript \"$CLAUDE_TRANSCRIPT_PATH\"" }
    ]
  }
}
EOF

# (Optional) Verify
memory-graph status
#   Should print JSON with total_nodes: 0 (fresh store).
```

If you'd rather run the three steps individually (more control, e.g.
choose your own CLAUDE.md target file), `setup` is sugar for:

```bash
memory-graph register             # → .mcp.json
memory-graph init                 # → .memory-graph/
memory-graph install-claude-md    # → memory protocol in CLAUDE.md
```

Restart any open Claude Code session in this directory. The 13
`memory_*` tools should be available. Sanity check:

> *"Call `memory_status` and show me what you see."*

### What this does NOT do

- Doesn't affect any other project's Claude Code behavior. Without a
  project-level `.mcp.json` (or a `~/.claude.json` entry — which we
  don't write here), other projects don't see the server.
- Doesn't commit anything. Decide per project whether to commit
  `.mcp.json` (depends on whether the token in it is sensitive),
  `.memory-graph/` (commit for shared team memory; gitignore for
  per-person), and `.claude/settings.json` (the Stop hook).

### Undo

```bash
memory-graph unregister              # removes the .mcp.json entry
rm -rf .memory-graph                 # delete the store
# (also remove the memory protocol section from CLAUDE.md by hand)
```

### Scope: project vs user

Default is project (`./.mcp.json`). For "every Claude Code session
everywhere sees it":

```bash
memory-graph register --scope user
```

Even then, the server is dormant in any project without a
`.memory-graph/` directory.

---

## Working on this repo

```bash
# Tests
.venv/bin/pytest -q

# Slow tests
FASTEMBED=1 .venv/bin/pytest tests/test_embed.py    # real model
CLAUDE_CODE_OAUTH_TOKEN=$TOKEN .venv/bin/pytest \
    tests/test_orchestration.py                     # real sub-agent

# Sub-agent prompts live as markdown files — edit and re-run, no
# code changes needed:
src/memory_graph/prompts/system.md
src/memory_graph/prompts/remember.md
src/memory_graph/prompts/retrieve.md
src/memory_graph/prompts/compact.md
```

## Layout reminder

```
src/memory_graph/
├── storage/        SQLite + markdown + Note model + ULID ids
├── embed/          Embedder protocol, FastEmbed, deterministic fake
├── primitives/     Store class with all memory operations (pure code)
├── orchestration/  Agent SDK runner + remember / retrieve / compact
├── prompts/        4 markdown prompt templates
├── server.py       FastMCP server registering 13 tools
└── cli.py          memory-graph: init / serve / digest / reindex /
                                  status / register / unregister
```

## Commit history (v0)

Build was 9 commits:

1. Project skeleton
2. Storage layer (SQLite + markdown + ULIDs)
3. Local embeddings (FastEmbed + deterministic fake)
4. Memory primitives (Store class)
5. MCP server (10 primitives)
6. Agent SDK orchestration (remember / retrieve / compact)
7. CLI (init / serve / digest / reindex / status)
8. Docs (INSTALL.md, CLAUDE.md template, README)
9. CLI register / unregister for one-shot config writing
