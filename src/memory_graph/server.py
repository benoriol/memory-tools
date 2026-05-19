"""MCP server exposing memory-graph primitives.

The server speaks JSON-RPC over stdio (FastMCP default). On startup it
resolves the project's `.memory-graph/` from $MEMORY_GRAPH_ROOT if set,
otherwise by walking up from the current working directory. The store
is loaded lazily on the first tool call.

The three "smart" tools (`remember`, `retrieve`, `compact`) that spawn
Agent-SDK sub-agents live alongside the primitives; they're optional and
only registered when the `claude-agent-sdk` dependency is installed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from memory_graph.embed import LocalEmbedder
from memory_graph.embed.base import Embedder
from memory_graph.primitives import Store
from memory_graph.storage import Edge, STORE_DIRNAME
from memory_graph.storage.files import store_root

mcp = FastMCP("memory-graph")

_store: Store | None = None
_store_root: Path | None = None


def _resolve_root() -> Path:
    """Find the project's `.memory-graph/` directory."""
    env = os.environ.get("MEMORY_GRAPH_ROOT")
    if env:
        p = Path(env).resolve()
        if not p.is_dir():
            raise FileNotFoundError(
                f"$MEMORY_GRAPH_ROOT points to {p}, which is not a directory."
            )
        return p
    return store_root()


def get_store() -> Store:
    """Lazy singleton store, scoped to the resolved root."""
    global _store, _store_root
    if _store is not None:
        return _store
    root = _resolve_root()
    embedder: Embedder = _make_embedder()
    _store = Store(root, embedder=embedder)
    _store_root = root
    return _store


def _make_embedder() -> Embedder:
    """Instantiate the configured embedder. Default: local FastEmbed."""
    # Future: read model name / provider from config.yml under the store root.
    return LocalEmbedder()


# ----------------------------------------------------------------------------
# Tools — pure primitives the main agent or sub-agents call.
# ----------------------------------------------------------------------------


@mcp.tool()
def memory_capture(
    title: str,
    summary: str,
    body: str,
    kind: str,
    status: str = "active",
    tags: list[str] | None = None,
    edges: list[dict[str, Any]] | None = None,
    happened_at: int | None = None,
    last_verified_at: int | None = None,
    confidence: float = 1.0,
) -> dict[str, Any]:
    """Write a single memory note to the store.

    `edges` is a list of {"to": id, "type": "...", "weight": 1.0}.
    Returns {"id": new_id, "duplicates": [...]}, where `duplicates` lists
    existing notes with cosine >= 0.92 to the new content.
    """
    edge_objs = [
        Edge(to_id=e["to"], type=e["type"], weight=float(e.get("weight", 1.0)))
        for e in (edges or [])
    ]
    return get_store().capture(
        title=title,
        summary=summary,
        body=body,
        kind=kind,
        status=status,
        tags=tags or [],
        edges=edge_objs,
        happened_at=happened_at,
        last_verified_at=last_verified_at,
        confidence=confidence,
    )


@mcp.tool()
def memory_capture_batch(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Capture many notes atomically. Items may use "@1", "@2" as placeholder
    ids in `note_id` and in `edges[*].to` for intra-batch references.
    """
    return get_store().capture_batch(notes)


@mcp.tool()
def memory_get(note_id: str) -> dict[str, Any] | None:
    """Fetch a single note's full content + edges + tags + anchors."""
    note = get_store().get(note_id)
    if note is None:
        return None
    return _serialize_note(note)


@mcp.tool()
def memory_search(
    query: str,
    k: int = 10,
    kind: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Semantic top-k by cosine similarity. Returns [{id, summary, kind, score}]."""
    return get_store().search(query, k=k, kind=kind, status=status)


@mcp.tool()
def memory_neighbors(
    note_id: str,
    types: list[str] | None = None,
    depth: int = 1,
    direction: str = "out",
) -> list[dict[str, Any]]:
    """Walk the graph from `note_id` along edge `types` up to `depth` hops.

    `direction` is "out", "in", or "both". Returns each neighbor with the
    edge_type used to reach it and the hop distance.
    """
    return get_store().neighbors(
        note_id, types=types, depth=depth, direction=direction
    )


@mcp.tool()
def memory_link(
    from_id: str, to_id: str, type: str, weight: float = 1.0
) -> dict[str, str]:
    """Add (or replace) a typed edge between two notes."""
    get_store().link(from_id, to_id, type, weight=weight)
    return {"ok": "linked", "from": from_id, "to": to_id, "type": type}


@mcp.tool()
def memory_unlink(from_id: str, to_id: str, type: str) -> dict[str, str]:
    """Remove a typed edge between two notes."""
    get_store().unlink(from_id, to_id, type)
    return {"ok": "unlinked", "from": from_id, "to": to_id, "type": type}


@mcp.tool()
def memory_supersede(old_id: str, new_id: str, reason: str = "") -> dict[str, str]:
    """Mark `old_id` as superseded by `new_id` and add a `supersedes` edge."""
    get_store().supersede(old_id=old_id, new_id=new_id, reason=reason)
    return {"ok": "superseded", "old": old_id, "new": new_id}


@mcp.tool()
def memory_mark(note_id: str, status: str) -> dict[str, str]:
    """Set a note's status (e.g. 'disputed', 'disproven', 'stale')."""
    get_store().mark(note_id, status)
    return {"ok": "marked", "id": note_id, "status": status}


@mcp.tool()
def memory_status() -> dict[str, Any]:
    """Counts by kind / status / edge_type, plus embedding model info."""
    return get_store().status()


# ----------------------------------------------------------------------------


def _serialize_note(note) -> dict[str, Any]:
    return {
        "id": note.id,
        "title": note.title,
        "summary": note.summary,
        "body": note.body,
        "kind": note.kind,
        "status": note.status,
        "created_at": note.created_at,
        "updated_at": note.updated_at,
        "happened_at": note.happened_at,
        "last_verified_at": note.last_verified_at,
        "confidence": note.confidence,
        "tags": list(note.tags),
        "edges": [
            {"to": e.to_id, "type": e.type, "weight": e.weight} for e in note.edges
        ],
        "anchors": [
            {"path": a.path, "pattern": a.pattern, "commit_sha": a.commit_sha}
            for a in note.anchors
        ],
    }


def main() -> None:
    """Entry point: run the MCP server on stdio."""
    # Touch STORE_DIRNAME so importers see it used (signals public API).
    _ = STORE_DIRNAME
    mcp.run()


if __name__ == "__main__":
    main()
