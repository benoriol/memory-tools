"""SQLite connection management and schema bookkeeping."""

from __future__ import annotations

import sqlite3
from importlib.resources import files
from pathlib import Path

SCHEMA_VERSION = 1
_SCHEMA_SQL = files("memory_graph.storage").joinpath("schema.sql").read_text()


def open_db(path: str | Path) -> sqlite3.Connection:
    """Open the SQLite index at `path`.

    The parent directory is created if it doesn't exist. Foreign keys
    and WAL journaling are enabled. The schema is applied idempotently
    and the `meta.schema_version` row is set on first creation.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA_SQL)
    _ensure_version(conn)
    return conn


def _ensure_version(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO meta(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        return
    current = int(row["value"])
    if current > SCHEMA_VERSION:
        raise RuntimeError(
            f"Store schema version {current} is newer than this code "
            f"({SCHEMA_VERSION}). Upgrade memory-graph-mcp."
        )


def get_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    return int(row["value"]) if row else 0
