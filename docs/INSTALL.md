# Install

Five steps. ~5 minutes once you have the OAuth token.

## 1. Generate a Claude Code OAuth token

```bash
claude setup-token
```

This walks you through OAuth and prints a long-lived token. Copy it
somewhere safe; you'll paste it into MCP config below. The token
authenticates against your Claude Pro/Max subscription so the memory
sub-agent doesn't need a separate Anthropic API key.

> Today, Agent SDK usage counts against your normal Claude Code
> interactive limits. Starting June 15, 2026, it gets its own
> monthly credit ($100/mo on Max 5x, $200/mo on Max 20x).

## 2. Install the package

```bash
git clone <this repo>
cd memory-module-mcp
pipx install -e .
```

`memory-graph` should now be on your PATH.

## 3. Register the MCP server with Claude Code

You have two options. Pick one.

### Option A — project-local (recommended for trying it out)

Only the project you're in will see the tool:

```bash
cd ~/projects/your-project
export CLAUDE_CODE_OAUTH_TOKEN=<paste the token from step 1>
memory-graph register
```

That writes `./.mcp.json` with an absolute path to the binary and your
token. Other projects are unaffected.

### Option B — user-global (every Claude Code session sees it)

```bash
export CLAUDE_CODE_OAUTH_TOKEN=<paste the token from step 1>
memory-graph register --scope user
```

That merges the entry into `~/.claude.json`. Even with this, the
server is dormant in any project that hasn't been `memory-graph init`'d
— each `.memory-graph/` directory is the actual data boundary.

### Manual alternative

If you prefer to write the config by hand, the file should look like:

```json
{
  "mcpServers": {
    "memory-graph": {
      "command": "/abs/path/to/memory-graph",
      "args": ["serve"],
      "env": {
        "CLAUDE_CODE_OAUTH_TOKEN": "<the token>"
      }
    }
  }
}
```

Drop it as `./.mcp.json` (project) or merge into `~/.claude.json` (user).

### Verify

Restart Claude Code. The 13 `memory_*` tools should be available
(10 primitives + `memory_remember` / `memory_retrieve` / `memory_compact`).

### Undo

```bash
memory-graph unregister             # project-local
memory-graph unregister --scope user # user-global
```

## 4. Initialize a project store

```bash
cd ~/projects/your-project
memory-graph init
```

That creates `.memory-graph/` with:

```
.memory-graph/
├── notes/         <- markdown notes, one per memory
├── _operator/     <- sub-agent's persistent working notes
├── _pending/      <- deferred items (review queue, etc.)
├── index.db       <- SQLite index (auto-rebuildable from notes/)
└── config.yml     <- embedding model, etc.
```

Decide whether to commit `.memory-graph/` to the repo. If you want
team members to share memory, commit it (the project's `.gitignore`
already excludes the SQLite index by default). If it's per-person,
add `.memory-graph/` to the project root's `.gitignore`.

## 5. Wire the memory protocol into the project's CLAUDE.md

Copy [`docs/CLAUDE.md.template`](./CLAUDE.md.template) into the
project's `CLAUDE.md` (or `.claude/CLAUDE.md`). Tweak the risky-path
list to match your project.

## Optional: Stop hook for automatic end-of-session digest

In your project's `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "command": "memory-graph digest --transcript \"$CLAUDE_TRANSCRIPT_PATH\""
      }
    ]
  }
}
```

After every Claude Code session ends, this fires the memory sub-agent
on the transcript to capture anything the main agent missed.

## Verify

```bash
cd ~/projects/your-project
memory-graph status
```

Should print stats as JSON with `total_nodes: 0` for a fresh store.

## Optional: pin the embedding model on first run

The first `memory_capture` (or `memory-graph status`) downloads
the embedding model to `~/.cache/huggingface/` (~80 MB). If you want
to pre-warm:

```bash
FASTEMBED=1 pytest tests/test_embed.py::test_local_embedder_real_model_smoke
```

(Run from inside this repo, with `[dev]` extras installed.)

## Updating

```bash
cd memory-module-mcp
git pull
# pipx install -e picks up source changes automatically; restart any
# running Claude Code session to get the new MCP server code.
```

If a schema bump landed, run `memory-graph reindex` in each project's
root to rebuild the SQLite index from the markdown notes.
