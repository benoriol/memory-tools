"""Dataclasses for a memory note and its associated structure.

The model is deliberately flat. There's one node type (any note); the
`kind` field is a free-text label whose only job is to help humans (and
the agent) describe a note at a glance. The system does not branch on it.

Edges are also a short, fixed vocabulary:

- `abstracts` (directed). `from_id → to_id` means the **from** note is
  *more abstract* than the **to** note. To walk upward (toward more
  abstract context) from a leaf, follow **incoming** abstracts edges;
  to walk downward (toward concrete detail) from a parent, follow
  outgoing ones.
- `related` (undirected in meaning, though the row has a direction).
  Lateral / associative connection.
- `supersedes` (directed). The new note replaces the old. Also flips
  `status='superseded'` on the old node — the only behavior-bearing
  edge.

Suggested labels: `user_said`, `experiment`, `mistake`, `bug_fix`,
`former_state`, `decision`, `principle`, `observation`. Free text —
new labels can appear without any schema change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Plain `str` aliases — no Literal constraint. The schema accepts any
# value; the canonical vocabulary is just a convention enforced by the
# sub-agent prompts and viz palette, not by the storage layer.
Kind = str
Status = str
EdgeType = str


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
    # A ≤5-word label the agent picks for compact UI rendering
    # (graph nodes, list rows). Falls back to `title` when None.
    short_label: str | None = None
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
