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

## 3. Bootstrap the project (one command)

```bash
cd ~/projects/your-project
export CLAUDE_CODE_OAUTH_TOKEN=<paste the token from step 1>
memory-graph setup
```

That single command does all three of the per-project things in order:

1. **register** — writes `./.mcp.json` with absolute binary path + token
2. **init** — creates `./.memory-graph/{notes,_operator,_pending,...}`
3. **install-claude-md** — appends the memory protocol to
   `./CLAUDE.md` (creating it if absent), wrapped in sentinel comments
   so the install command can be re-run without clobbering your edits.

It's idempotent — re-running is a no-op. Pass `--force` to replace an
existing `.mcp.json` entry or a stale CLAUDE.md section. Pass any of
`--skip-register`, `--skip-init`, `--skip-claude-md` to do only some
of the steps.

### Doing the steps individually

If you want more control (different CLAUDE.md path, user-scope MCP,
etc.):

```bash
memory-graph register [--scope project|user]   # → .mcp.json or ~/.claude.json
memory-graph init                              # → .memory-graph/
memory-graph install-claude-md [--target ...]  # → memory protocol section
```

`--scope user` makes the MCP server visible in every Claude Code
session everywhere; the server stays dormant in any project that
doesn't have a `.memory-graph/` directory. Most users want the default
(project scope) so unrelated projects keep clean tool lists.

### Manual alternative (no CLI)

If you prefer to write the config by hand, `./.mcp.json` should look
like:

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

Drop it as `./.mcp.json` (project scope) or merge into `~/.claude.json`
(user scope).

### Verify

Restart Claude Code. The 13 `memory_*` tools should be available
(10 primitives + `memory_remember` / `memory_retrieve` / `memory_compact`).

### Undo

```bash
memory-graph unregister             # project-local
memory-graph unregister --scope user # user-global
```

## 4. Decide what to commit

`memory-graph setup` produces three artifacts in your project:

| File / dir          | What it is                       | Commit?                                              |
|---------------------|----------------------------------|------------------------------------------------------|
| `.mcp.json`         | MCP server registration + token  | Only if your team also uses memory-graph and you're OK with the token in git. Usually `.gitignore` it. |
| `.memory-graph/`    | Notes + SQLite index             | Commit for shared team memory; `.gitignore` for per-person. The internal SQLite index is already gitignored either way (rebuildable from `notes/`). |
| `CLAUDE.md` section | The memory protocol              | Yes — it's part of your project's instructions.      |

To gitignore the registration + per-person notes:

```bash
echo ".mcp.json"        >> .gitignore
echo ".memory-graph/"   >> .gitignore
```

The protocol block in `CLAUDE.md` stays — it documents the workflow
for the next session and for collaborators.

The template at [`docs/CLAUDE.md.template`](./CLAUDE.md.template) is
the same content as what `install-claude-md` writes, kept here for
reference; the source of truth lives in the package at
`src/memory_graph/templates/claude_protocol.md`.

If you ever need to remove the protocol section:

```bash
memory-graph uninstall-claude-md
```

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
