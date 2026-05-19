"""Storage layer: SQLite index + markdown files."""

from memory_graph.storage.db import SCHEMA_VERSION, open_db
from memory_graph.storage.files import (
    NOTES_DIRNAME,
    STORE_DIRNAME,
    read_note,
    store_root,
    write_note,
)
from memory_graph.storage.ids import new_id
from memory_graph.storage.note import Anchor, Edge, Note

__all__ = [
    "Anchor",
    "Edge",
    "NOTES_DIRNAME",
    "Note",
    "SCHEMA_VERSION",
    "STORE_DIRNAME",
    "new_id",
    "open_db",
    "read_note",
    "store_root",
    "write_note",
]
