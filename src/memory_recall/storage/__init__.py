"""Storage layer: SQLite + markdown files."""

from memory_recall.storage.note import Note, NoteView

STORE_DIRNAME = ".memory-recall"

__all__ = ["STORE_DIRNAME", "Note", "NoteView"]
