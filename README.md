# memory-graph-mcp

Per-project graph memory for Claude Code, exposed as an MCP server.

Notes are stored as markdown files with YAML frontmatter; a SQLite index
provides fast lookups and embedding-based semantic search. Edges between notes
form a typed graph (`generalizes`, `derived_from`, `coupled_with`, `supersedes`,
etc.) that the agent navigates instead of relying purely on similarity.

This is a work in progress. The pieces land in this order:

1. Project skeleton (this commit)
2. Storage layer: SQLite schema, markdown I/O, `Note` model
3. Local embeddings (FastEmbed)
4. Pure primitives: `capture`, `get`, `search`, `neighbors`, `link`, `supersede`, `status`
5. MCP server wrapping the primitives
6. Agent-SDK-backed `remember`, `retrieve`, `compact` tools
7. CLI: `init`, `digest`, `reindex`
8. CLAUDE.md template and install docs

## Layout

```
src/memory_graph/      Library code
tests/                 Pytest suite
```

## Status

Pre-alpha. Don't depend on the schema yet.
