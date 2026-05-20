-- memory-graph SQLite schema.
-- Bodies live in markdown files; this DB is a derived index.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
    id                TEXT PRIMARY KEY,
    title             TEXT NOT NULL,
    -- `short_label` is a ≤5-word label the agent picks for compact UI
    -- rendering (graph viz, list rows). Falls back to title when NULL.
    short_label       TEXT,
    summary           TEXT NOT NULL,
    body              TEXT NOT NULL,
    -- `kind` is a free-text label for the reader's orientation
    -- (e.g. 'experiment', 'mistake', 'user_said', 'bug_fix',
    --  'former_state', 'principle'). The system does not branch on it.
    kind              TEXT NOT NULL,
    -- `status` IS behavior-bearing (drives retrieval emphasis and
    -- supersession): one of 'active', 'unsure', 'superseded',
    -- 'disproven', 'stale', 'archived'.
    status            TEXT NOT NULL DEFAULT 'active',
    created_at        INTEGER NOT NULL,
    updated_at        INTEGER NOT NULL,
    -- Optional event/verification timestamps — both available on every
    -- note; pick whichever fits the content. Either may be NULL.
    happened_at       INTEGER,
    last_verified_at  INTEGER,
    confidence        REAL    NOT NULL DEFAULT 1.0,
    cluster_id        INTEGER,
    -- sha256 of the embed-input (title + summary + body prefix); used to
    -- decide whether the embedding needs to be regenerated on save.
    body_hash         TEXT,
    -- absolute path to the markdown file backing this node, if any.
    source_path       TEXT
);

CREATE INDEX IF NOT EXISTS idx_nodes_kind   ON nodes(kind);
CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status);
CREATE INDEX IF NOT EXISTS idx_nodes_cluster ON nodes(cluster_id);

-- Edges. v2 vocabulary is just three types:
--   'abstracts' — directed: from_id is MORE ABSTRACT than to_id.
--                 Walking outgoing -> concrete detail.
--                 Walking incoming -> abstract context.
--   'related'   — lateral / associative.
--   'supersedes'— directed: from_id replaces to_id; also flips
--                 to_id.status to 'superseded'.
-- The column is plain TEXT (no CHECK constraint) so new edge types
-- can be added without a schema bump if/when needed.
CREATE TABLE IF NOT EXISTS edges (
    from_id     TEXT NOT NULL,
    to_id       TEXT NOT NULL,
    type        TEXT NOT NULL,
    weight      REAL NOT NULL DEFAULT 1.0,
    created_at  INTEGER NOT NULL,
    PRIMARY KEY (from_id, to_id, type),
    FOREIGN KEY (from_id) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (to_id)   REFERENCES nodes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id, type);
CREATE INDEX IF NOT EXISTS idx_edges_to   ON edges(to_id, type);

CREATE TABLE IF NOT EXISTS tags (
    node_id TEXT NOT NULL,
    tag     TEXT NOT NULL,
    PRIMARY KEY (node_id, tag),
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);

-- Anchors tie an archaeology / reference note to specific code artifacts.
-- The (path, pattern, commit_sha) triple lets staleness checks compare
-- against the current file contents.
CREATE TABLE IF NOT EXISTS anchors (
    node_id     TEXT NOT NULL,
    path        TEXT NOT NULL,
    pattern     TEXT NOT NULL DEFAULT '',
    commit_sha  TEXT,
    PRIMARY KEY (node_id, path, pattern),
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_anchors_path ON anchors(path);

-- Embeddings. Stored as raw BLOB of float32; cosine similarity is computed
-- in Python (numpy) for v0. For larger stores, swap in sqlite-vec without
-- changing the column shape.
CREATE TABLE IF NOT EXISTS embeddings (
    node_id     TEXT PRIMARY KEY,
    body_hash   TEXT NOT NULL,
    vector      BLOB NOT NULL,
    dim         INTEGER NOT NULL,
    model       TEXT NOT NULL,
    created_at  INTEGER NOT NULL,
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
);
