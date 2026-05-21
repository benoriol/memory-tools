"""Dataclasses for notes and their retrieval views."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Note:
    """One memory note as stored on disk and in SQLite."""

    id: str
    title: str
    summary: str
    body: str
    tags: list[str] = field(default_factory=list)
    created_at: int = 0
    updated_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class NoteView:
    """One retrieval view (summary / keyword / paraphrase) of a note."""

    id: int
    note_id: str
    view_kind: str
    view_text: str
    embedding: np.ndarray
