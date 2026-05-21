"""SQLite connection helpers and embedding serialization."""

from __future__ import annotations

import sqlite3
from importlib import resources
from pathlib import Path

import numpy as np

_DB_FILENAME = "store.db"


def db_path(root: Path) -> Path:
    return root / _DB_FILENAME


def connect(root: Path) -> sqlite3.Connection:
    """Open (creating if needed) the SQLite db inside `root` and apply schema."""
    path = db_path(root)
    # `check_same_thread=False` lets the FastAPI viz server share one connection
    # across threadpool workers. Internal writes are serialized via `with self.conn:`.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    schema = resources.files("memory_recall.storage").joinpath("schema.sql").read_text()
    conn.executescript(schema)
    conn.commit()
    return conn


def pack_embedding(vec: np.ndarray) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def unpack_embedding(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)
