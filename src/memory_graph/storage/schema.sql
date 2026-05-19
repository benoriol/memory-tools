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
    summary           TEXT NOT NULL,
    body              TEXT NOT NULL,
    kind              TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'active',
    created_at        INTEGER NOT NULL,
    updated_at        INTEGER NOT NULL,
    -- eventive notes (experiment, decision, incident, transition, archaeology)
    -- carry a happened_at; stative notes (reference) carry last_verified_at.
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
