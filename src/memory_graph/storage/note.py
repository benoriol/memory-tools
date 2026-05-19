"""Dataclasses for a memory note and its associated structure."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Kind = Literal[
    "capture",
    "lesson",
    "principle",
    "decision",
    "experiment",
    "incident",
    "reference",
    "transition",
    "archaeology",
    "next_step",
]

Status = Literal[
    "active",
    "validated",
    "unsure",
    "disputed",
    "superseded",
    "corrected",
    "disproven",
    "stale",
    "open",      # for next_step kinds
    "archived",
]

EdgeType = Literal[
    "generalizes",
    "specializes",
    "derived_from",
    "supports",
    "contradicts",
    "supersedes",
    "corrects",
    "applies_to",
    "coupled_with",
    "impacts",
    "informs",
    "confirmed_by",
    "related",
]


@dataclass(slots=True)
class Edge:
    """A typed edge between two notes."""

    to_id: str
    type: str  # one of EdgeType, but stored loose to permit future kinds
    weight: float = 1.0


@dataclass(slots=True)
class Anchor:
    """Pins a note to a code artifact for staleness checks."""

    path: str
    pattern: str = ""
    commit_sha: str | None = None


@dataclass(slots=True)
class Note:
    """A single memory note, mirroring what's on disk and in the index."""

    id: str
    title: str
    summary: str
    body: str
    kind: str
    status: str = "active"
    created_at: int = 0           # ms since epoch
    updated_at: int = 0
    happened_at: int | None = None
    last_verified_at: int | None = None
    confidence: float = 1.0
    tags: list[str] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    anchors: list[Anchor] = field(default_factory=list)
    cluster_id: int | None = None
    body_hash: str | None = None
    source_path: str | None = None
