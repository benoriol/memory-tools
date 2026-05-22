# memory_recall — design

Replaces `memory_graph`. The graph approach is gone. The new approach
is **multi-vector recall** over a flat list of memory notes.

## Core idea

When you capture a memory:

1. A sub-agent expands the raw input into several *retrieval views*:
   - the canonical summary,
   - 3–5 keyword phrases,
   - 2–3 paraphrased canonical sentences (different ways someone might
     ask about this).
2. Every view is embedded independently and stored.
3. The note body, summary, and metadata are kept verbatim.

When you search:

1. A sub-agent expands the raw query into several *query views*: a
   keyword set, 2–3 canonical paraphrases, the verbatim query.
2. Every view is embedded.
3. For each (note, query-view × note-view) pair we compute cosine
   similarity. The note's score is `max` over all pairs.
4. Top-k notes are returned with their body + summary.

This is multi-vector late-interaction retrieval, simplified. The
agent itself does the view-generation (no separate IR model).

## What's gone

- The `Edge` / `memory_neighbors` / `memory_link` graph machinery.
- The `kind`/`status` hierarchy where notes were structurally
  classified.
- `memory_remember` / `memory_retrieve` / `memory_compact` orchestrators.
- Anchors, parent/child note relations, the operator context file,
  the `_pending` queue.

What remains conceptually: a SQLite + markdown store, FastEmbed for
embeddings, an MCP server, a CLI.

## Storage schema

SQLite tables:

```sql
CREATE TABLE notes (
  id          TEXT PRIMARY KEY,
  title       TEXT NOT NULL,
  summary     TEXT NOT NULL,
  body        TEXT NOT NULL,
  tags        TEXT NOT NULL,          -- JSON array of strings
  created_at  INTEGER NOT NULL,       -- epoch ms
  updated_at  INTEGER NOT NULL
);

CREATE TABLE note_views (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  note_id     TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  view_kind   TEXT NOT NULL,          -- 'summary' | 'keyword' | 'paraphrase'
  view_text   TEXT NOT NULL,
  embedding   BLOB NOT NULL           -- packed float32 (384 dims for MiniLM)
);

CREATE INDEX idx_views_note ON note_views(note_id);
```

Each note also gets a markdown file `notes/<id>.md` with frontmatter
+ body, for human inspection.

## Tools (MCP)

Total: 5. No graph tools.

| Tool | Purpose |
|------|---------|
| `memory_capture(content, tags?)` | Hand off raw text to the capture sub-agent. Returns `{id, summary, views: [..]}`. |
| `memory_retrieve_candidates(query, k=10)` | **STEP 1 of recall.** Open-ended query → sub-agent expansion → top-k candidate summaries (`{id, summary, score, matched_view}`, no body). |
| `memory_get(ids)` | **STEP 2 of recall.** Fetch full bodies of one or more chosen candidates in a single batched call. |
| `memory_list(limit=100, offset=0)` | Browse all notes (paginated). |
| `memory_status()` | Summary stats: count, embedding model, recent activity. |

**Two-step recall is the load-bearing API choice.** The main agent
asks generously (k=10, open-ended input) at step 1 for cheap
summaries, then makes a deliberate per-candidate decision about which
to expand at step 2. This keeps the typical retrieval well under
~1000 tokens of context and lets the main agent — not the memory
layer — decide what's relevant.

## Sub-agents

Two small `claude_agent_sdk.query()` calls, one for capture, one for
search. Their job is text-to-text: take input, emit structured JSON
with the views.

Capture sub-agent prompt (sketch):

> Given this raw note, output JSON: `{summary: str, keywords: [str],
> paraphrases: [str]}`. Summary is a single declarative sentence.
> Keywords are 3–5 short noun phrases. Paraphrases are 2–3 ways
> someone might ask a question that this note answers, in canonical
> engineering vocabulary.

Search sub-agent prompt (sketch):

> Given this raw query, output JSON: `{keywords: [str],
> paraphrases: [str]}`. Keywords are 3–5 short noun phrases extracted
> from the query. Paraphrases are 2–3 alternative ways to ask the
> same question in canonical engineering vocabulary.

Default sub-agent model: Sonnet 4.6 effort=low. Configurable via env
var `MEMORY_RECALL_SUBAGENT_MODEL` (so we can swap to Haiku for
benchmarking).

## CLI

```
memory-recall init [DIR]      # create .memory-recall/ in DIR
memory-recall serve           # run the MCP server on stdio
memory-recall status          # print stats as JSON
memory-recall viz [--port N]  # start the FastAPI visualization server
memory-recall register        # write .mcp.json entry (project-scoped by default)
memory-recall unregister
```

## Visualization server

FastAPI app on `localhost:8765` (configurable). Serves:

- `GET /` — single-page HTML+JS frontend.
- `GET /api/notes` — list all notes with `{id, summary, tags,
  created_at, embedding_2d: [x, y]}`. The 2D projection is computed
  on the fly via PCA over the *summary* embeddings (one point per
  note).
- `GET /api/notes/{id}` — full note detail incl. all views.
- `POST /api/search` — body `{query: str, k: int}`. Invokes the
  search sub-agent and returns ranked notes plus the expanded views
  that were embedded.
- `DELETE /api/notes/{id}` — remove a note (and its views, files,
  markdown).

Frontend (vanilla HTML + plotly + minimal CSS):

- Left pane: list of notes (id, title, created_at, tags).
- Right pane: tab between
  - **Cluster** — 2D plotly scatter, one point per note, colored by
    tag-cluster or just one color.
  - **Detail** — selected note's summary + body + views.
- Top: search box. On submit, calls `POST /api/search`, shows ranked
  results in the list pane, and also displays the sub-agent's
  expanded views so you can see what was actually searched.

## Tests

Pytest suite:

- `test_db.py` — schema migrations, CRUD.
- `test_embed.py` — embedder shape + determinism.
- `test_store.py` — capture, search, multi-vector pooling correctness.
- `test_subagent.py` — mocked sub-agent JSON parsing + error paths.
- `test_server.py` — MCP tool registration + roundtrip.
- `test_cli.py` — init / status commands.

## Benchmark

`demos/eval/experiments/e25_multivec_vs_singlevec/` — recall-stress
task. Corpus of 50 notes, each with a canonical fact. 50 queries
phrased orthogonally to the note bodies (different vocabulary, same
referent). Three arms:

- **grep-only**: agent uses Bash + Grep over a `notes/` directory.
- **single-vector**: one embedding per note (the body). Same agent
  but with a custom retrieval tool.
- **multi-vector**: this design (sub-agent generates views; max-pool
  across views).

Measure recall@1, recall@5, cost, latency.

## Out of scope (for now)

- API-based embeddings.
- Dedup / merge.
- Memory pruning / decay.
- Cross-project shared memory.
- The graph/abstraction-layer experiments from `experiments/PLAN.md`
  (they can come back if benchmarks suggest structure helps).
