CREATE TABLE IF NOT EXISTS notes (
  id          TEXT PRIMARY KEY,
  title       TEXT NOT NULL,
  summary     TEXT NOT NULL,
  body        TEXT NOT NULL,
  tags        TEXT NOT NULL,
  created_at  INTEGER NOT NULL,
  updated_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS note_views (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  note_id     TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  view_kind   TEXT NOT NULL,
  view_text   TEXT NOT NULL,
  embedding   BLOB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_views_note ON note_views(note_id);
