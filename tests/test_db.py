"""SQLite schema + CRUD tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from memory_recall.storage.db import connect, pack_embedding, unpack_embedding


def test_schema_creates_tables(store_root: Path) -> None:
    conn = connect(store_root)
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "notes" in tables
    assert "note_views" in tables


def test_roundtrip(store_root: Path) -> None:
    conn = connect(store_root)
    conn.execute(
        "INSERT INTO notes (id, title, summary, body, tags, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("n1", "t", "s", "b", "[]", 1, 1),
    )
    emb = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    conn.execute(
        "INSERT INTO note_views (note_id, view_kind, view_text, embedding) "
        "VALUES (?, ?, ?, ?)",
        ("n1", "summary", "s", pack_embedding(emb)),
    )
    row = conn.execute("SELECT * FROM note_views WHERE note_id = 'n1'").fetchone()
    out = unpack_embedding(row["embedding"])
    assert np.allclose(out, emb)


def test_cascade_delete(store_root: Path) -> None:
    conn = connect(store_root)
    conn.execute(
        "INSERT INTO notes (id, title, summary, body, tags, created_at, updated_at) "
        "VALUES ('n1', 't', 's', 'b', '[]', 1, 1)"
    )
    for kind in ("summary", "keyword", "paraphrase"):
        conn.execute(
            "INSERT INTO note_views (note_id, view_kind, view_text, embedding) "
            "VALUES ('n1', ?, ?, ?)",
            (kind, kind, pack_embedding(np.zeros(4, dtype=np.float32))),
        )
    conn.commit()
    conn.execute("DELETE FROM notes WHERE id = 'n1'")
    conn.commit()
    remaining = conn.execute(
        "SELECT COUNT(*) AS n FROM note_views WHERE note_id = 'n1'"
    ).fetchone()["n"]
    assert remaining == 0


def test_pack_unpack_dtype() -> None:
    v = np.arange(384, dtype=np.float32)
    blob = pack_embedding(v)
    assert isinstance(blob, bytes)
    assert len(blob) == 384 * 4
    out = unpack_embedding(blob)
    assert out.dtype == np.float32
    assert np.array_equal(out, v)
