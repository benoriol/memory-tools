"""SQLite open/migrate."""

from pathlib import Path

from memory_graph.storage import SCHEMA_VERSION, open_db
from memory_graph.storage.db import get_schema_version


def test_open_db_creates_file_and_tables(tmp_path: Path):
    db_path = tmp_path / "index.db"
    conn = open_db(db_path)
    try:
        assert db_path.exists()
        # Required tables.
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for required in {"meta", "nodes", "edges", "tags", "anchors"}:
            assert required in tables, f"missing table: {required}"
        assert get_schema_version(conn) == SCHEMA_VERSION
    finally:
        conn.close()


def test_open_db_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "index.db"
    conn1 = open_db(db_path)
    conn1.close()
    # Reopen should not error and version should be unchanged.
    conn2 = open_db(db_path)
    try:
        assert get_schema_version(conn2) == SCHEMA_VERSION
    finally:
        conn2.close()


def test_foreign_keys_enabled(tmp_path: Path):
    conn = open_db(tmp_path / "index.db")
    try:
        result = conn.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1
    finally:
        conn.close()


def test_edge_cascade_deletes_when_node_removed(tmp_path: Path):
    conn = open_db(tmp_path / "index.db")
    try:
        conn.execute(
            "INSERT INTO nodes(id,title,summary,body,kind,created_at,updated_at)"
            " VALUES('A','t','s','b','capture',0,0)"
        )
        conn.execute(
            "INSERT INTO nodes(id,title,summary,body,kind,created_at,updated_at)"
            " VALUES('B','t','s','b','capture',0,0)"
        )
        conn.execute(
            "INSERT INTO edges(from_id,to_id,type,created_at) VALUES('A','B','related',0)"
        )
        conn.execute("DELETE FROM nodes WHERE id='A'")
        rows = conn.execute("SELECT * FROM edges").fetchall()
        assert rows == []
    finally:
        conn.close()


