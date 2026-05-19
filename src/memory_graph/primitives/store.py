"""The `Store` wraps the SQLite index, the markdown files, and the embedder.

All memory primitives live as methods on `Store`. They never call an
LLM; orchestration (sub-agents that decompose, rerank, consolidate)
sits on top of these via the Agent SDK and is implemented elsewhere.
"""

from __future__ import annotations

import sqlite3
import time
from collections import deque
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from memory_graph.embed.base import (
    Embedder,
    build_embed_input,
    cosine,
    hash_input,
    normalize,
)
from memory_graph.storage import (
    Anchor,
    Edge,
    Note,
    NOTES_DIRNAME,
    new_id,
    open_db,
    write_note,
)

DUPLICATE_THRESHOLD = 0.92  # cosine; tuned for short summaries
TOP_K_DEFAULT = 10


class Store:
    """A per-project memory store."""

    def __init__(self, root: str | Path, embedder: Embedder):
        self.root = Path(root)
        self.embedder = embedder
        (self.root / NOTES_DIRNAME).mkdir(parents=True, exist_ok=True)
        self.conn: sqlite3.Connection = open_db(self.root / "index.db")

    # -- lifecycle ----------------------------------------------------------

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- capture ------------------------------------------------------------

    def capture(
        self,
        *,
        title: str,
        summary: str,
        body: str,
        kind: str,
        status: str = "active",
        tags: Iterable[str] = (),
        edges: Iterable[Edge] = (),
        anchors: Iterable[Anchor] = (),
        happened_at: int | None = None,
        last_verified_at: int | None = None,
        confidence: float = 1.0,
        note_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a note, embed it, persist it, and return id + flags.

        Returns a dict with:
          - id: the new note's id
          - duplicates: list of {id, summary, score} that exceed DUPLICATE_THRESHOLD
            (the caller decides whether to merge or proceed)
        """
        now = _now_ms()
        nid = note_id or new_id(now_ms=now)
        note = Note(
            id=nid,
            title=title,
            summary=summary,
            body=body,
            kind=kind,
            status=status,
            created_at=now,
            updated_at=now,
            tags=list(tags),
            edges=list(edges),
            anchors=list(anchors),
            happened_at=happened_at,
            last_verified_at=last_verified_at,
            confidence=confidence,
        )

        # Embed; reuse existing vector if the input hash matches (only matters
        # on re-capture / update flows).
        embed_text = build_embed_input(note.title, note.summary, note.body)
        note.body_hash = hash_input(embed_text)
        vec = self.embedder.embed(embed_text)

        # Duplicate detection happens *before* we insert so the caller can
        # decide to merge instead of writing.
        duplicates = self._duplicate_candidates(vec, exclude_id=nid)

        # Persist to DB + markdown.
        self._insert_node(note)
        self._upsert_embedding(nid, note.body_hash, vec)
        path = write_note(self.root, note)
        self.conn.execute(
            "UPDATE nodes SET source_path = ? WHERE id = ?", (str(path), nid)
        )

        return {"id": nid, "duplicates": duplicates}

    def capture_batch(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Capture many notes atomically, with intra-batch references.

        An item may set `note_id` to a placeholder starting with `@` (e.g.
        `"@1"`); edges may then reference these placeholders before they're
        resolved. Real ids are assigned in two passes:

          1. Walk items, mint real ids for each placeholder.
          2. Walk items again, swap placeholders in `edges[*].to_id`, and
             call `capture()` per item.
        """
        # Pass 1: resolve placeholders to real ids.
        id_map: dict[str, str] = {}
        for item in items:
            placeholder = item.get("note_id")
            if isinstance(placeholder, str) and placeholder.startswith("@"):
                id_map[placeholder] = new_id()

        # Pass 2: write each item with refs resolved.
        results: list[dict[str, Any]] = []
        for item in items:
            it = dict(item)
            ph = it.get("note_id")
            if isinstance(ph, str) and ph.startswith("@"):
                it["note_id"] = id_map[ph]
            edges = it.get("edges") or []
            resolved_edges: list[Edge] = []
            for e in edges:
                to = e.to_id if isinstance(e, Edge) else e["to"]
                if isinstance(to, str) and to.startswith("@"):
                    to = id_map.get(to, to)
                etype = e.type if isinstance(e, Edge) else e["type"]
                weight = e.weight if isinstance(e, Edge) else float(e.get("weight", 1.0))
                resolved_edges.append(Edge(to_id=to, type=etype, weight=weight))
            it["edges"] = resolved_edges
            results.append(self.capture(**it))
        return results

    # -- read ---------------------------------------------------------------

    def get(self, note_id: str) -> Note | None:
        """Fetch a Note by id (including its edges, tags, anchors)."""
        row = self.conn.execute(
            "SELECT * FROM nodes WHERE id = ?", (note_id,)
        ).fetchone()
        if row is None:
            return None
        edges = [
            Edge(to_id=r["to_id"], type=r["type"], weight=float(r["weight"]))
            for r in self.conn.execute(
                "SELECT to_id, type, weight FROM edges WHERE from_id = ?", (note_id,)
            )
        ]
        tags = [
            r["tag"] for r in self.conn.execute(
                "SELECT tag FROM tags WHERE node_id = ? ORDER BY tag", (note_id,)
            )
        ]
        anchors = [
            Anchor(path=r["path"], pattern=r["pattern"], commit_sha=r["commit_sha"])
            for r in self.conn.execute(
                "SELECT path, pattern, commit_sha FROM anchors WHERE node_id = ?",
                (note_id,),
            )
        ]
        return Note(
            id=row["id"],
            title=row["title"],
            summary=row["summary"],
            body=row["body"],
            kind=row["kind"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            happened_at=row["happened_at"],
            last_verified_at=row["last_verified_at"],
            confidence=row["confidence"],
            cluster_id=row["cluster_id"],
            body_hash=row["body_hash"],
            source_path=row["source_path"],
            tags=tags,
            edges=edges,
            anchors=anchors,
        )

    def search(
        self,
        query: str,
        *,
        k: int = TOP_K_DEFAULT,
        kind: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic top-k by cosine similarity. Returns id+summary+score+kind."""
        q_vec = self.embedder.embed(query)
        rows = self._load_embeddings(kind=kind, status=status)
        if not rows:
            return []
        ids = [r["node_id"] for r in rows]
        mat = np.vstack([_blob_to_vec(r["vector"], r["dim"]) for r in rows])
        # All vectors are L2-normalized, so cosine = dot product.
        q_norm = normalize(q_vec)
        scores = mat @ q_norm
        # Top-k by descending score.
        order = np.argsort(-scores)[: max(k, 0)]
        results = []
        for idx in order:
            nid = ids[idx]
            score = float(scores[idx])
            meta = self.conn.execute(
                "SELECT summary, kind, status FROM nodes WHERE id = ?", (nid,)
            ).fetchone()
            if meta is None:
                continue
            results.append({
                "id": nid,
                "summary": meta["summary"],
                "kind": meta["kind"],
                "status": meta["status"],
                "score": score,
            })
        return results

    def neighbors(
        self,
        note_id: str,
        *,
        types: Iterable[str] | None = None,
        depth: int = 1,
        direction: str = "out",  # "out" | "in" | "both"
    ) -> list[dict[str, Any]]:
        """Walk the graph from `note_id` up to `depth` hops along `types`.

        Returns each visited node (excluding the seed) with the edge type
        used to reach it and its distance in hops.
        """
        types_list = list(types) if types is not None else None
        seen: dict[str, dict[str, Any]] = {}
        queue: deque[tuple[str, int]] = deque([(note_id, 0)])
        visited: set[str] = {note_id}
        while queue:
            cur, dist = queue.popleft()
            if dist >= depth:
                continue
            for nxt_id, etype in self._step(cur, types_list, direction):
                if nxt_id in visited:
                    continue
                visited.add(nxt_id)
                meta = self.conn.execute(
                    "SELECT summary, kind, status FROM nodes WHERE id = ?",
                    (nxt_id,),
                ).fetchone()
                if meta is None:
                    continue
                seen[nxt_id] = {
                    "id": nxt_id,
                    "summary": meta["summary"],
                    "kind": meta["kind"],
                    "status": meta["status"],
                    "edge_type": etype,
                    "distance": dist + 1,
                }
                queue.append((nxt_id, dist + 1))
        return list(seen.values())

    # -- edges --------------------------------------------------------------

    def link(
        self,
        from_id: str,
        to_id: str,
        type: str,
        *,
        weight: float = 1.0,
    ) -> None:
        """Insert (or replace) an edge between two notes."""
        self.conn.execute(
            "INSERT OR REPLACE INTO edges(from_id, to_id, type, weight, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (from_id, to_id, type, weight, _now_ms()),
        )

    def unlink(self, from_id: str, to_id: str, type: str) -> None:
        self.conn.execute(
            "DELETE FROM edges WHERE from_id = ? AND to_id = ? AND type = ?",
            (from_id, to_id, type),
        )

    def supersede(self, old_id: str, new_id: str, reason: str = "") -> None:
        """Mark `old_id` as superseded by `new_id` and add a `supersedes` edge.

        Edge direction: new --supersedes--> old (the new note owns the rel).
        The `reason` is stored as part of the new note's body via the edge's
        weight today (no schema for reasons in v0); future versions may add
        an edge-attributes table.
        """
        self.link(new_id, old_id, "supersedes")
        self.conn.execute(
            "UPDATE nodes SET status = 'superseded', updated_at = ? WHERE id = ?",
            (_now_ms(), old_id),
        )
        # The reason is currently unused by storage; keep the argument for
        # API stability so callers don't churn when we add an edge-attributes
        # table in v1.
        _ = reason

    def mark(self, note_id: str, status: str) -> None:
        self.conn.execute(
            "UPDATE nodes SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now_ms(), note_id),
        )

    # -- stats --------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        counts_by_kind = {
            r["kind"]: r["n"]
            for r in self.conn.execute(
                "SELECT kind, COUNT(*) AS n FROM nodes GROUP BY kind"
            )
        }
        counts_by_status = {
            r["status"]: r["n"]
            for r in self.conn.execute(
                "SELECT status, COUNT(*) AS n FROM nodes GROUP BY status"
            )
        }
        edge_counts = {
            r["type"]: r["n"]
            for r in self.conn.execute(
                "SELECT type, COUNT(*) AS n FROM edges GROUP BY type"
            )
        }
        total_nodes = self.conn.execute(
            "SELECT COUNT(*) AS n FROM nodes"
        ).fetchone()["n"]
        total_edges = self.conn.execute(
            "SELECT COUNT(*) AS n FROM edges"
        ).fetchone()["n"]
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "by_kind": counts_by_kind,
            "by_status": counts_by_status,
            "by_edge_type": edge_counts,
            "embedding_model": self.embedder.name,
            "embedding_dim": self.embedder.dim,
        }

    # -- internals ----------------------------------------------------------

    def _insert_node(self, note: Note) -> None:
        with self.conn:
            self.conn.execute(
                """INSERT INTO nodes (
                    id, title, summary, body, kind, status, created_at, updated_at,
                    happened_at, last_verified_at, confidence, cluster_id, body_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    note.id, note.title, note.summary, note.body, note.kind,
                    note.status, note.created_at, note.updated_at,
                    note.happened_at, note.last_verified_at, note.confidence,
                    note.cluster_id, note.body_hash,
                ),
            )
            for tag in dict.fromkeys(note.tags):  # de-dupe, keep order
                self.conn.execute(
                    "INSERT OR IGNORE INTO tags(node_id, tag) VALUES (?, ?)",
                    (note.id, tag),
                )
            for e in note.edges:
                self.conn.execute(
                    "INSERT OR REPLACE INTO edges(from_id, to_id, type, weight, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (note.id, e.to_id, e.type, e.weight, note.created_at),
                )
            for a in note.anchors:
                self.conn.execute(
                    "INSERT OR REPLACE INTO anchors(node_id, path, pattern, commit_sha)"
                    " VALUES (?, ?, ?, ?)",
                    (note.id, a.path, a.pattern, a.commit_sha),
                )

    def _upsert_embedding(self, node_id: str, body_hash: str, vec: np.ndarray) -> None:
        self.conn.execute(
            """INSERT INTO embeddings(node_id, body_hash, vector, dim, model, created_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(node_id) DO UPDATE SET
                 body_hash = excluded.body_hash,
                 vector    = excluded.vector,
                 dim       = excluded.dim,
                 model     = excluded.model,
                 created_at = excluded.created_at""",
            (
                node_id, body_hash, _vec_to_blob(vec), self.embedder.dim,
                self.embedder.name, _now_ms(),
            ),
        )

    def _load_embeddings(
        self,
        *,
        kind: str | None = None,
        status: str | None = None,
    ) -> list[sqlite3.Row]:
        sql = (
            "SELECT e.node_id AS node_id, e.vector AS vector, e.dim AS dim "
            "FROM embeddings e JOIN nodes n ON n.id = e.node_id"
        )
        clauses, args = [], []
        if kind is not None:
            clauses.append("n.kind = ?")
            args.append(kind)
        if status is not None:
            clauses.append("n.status = ?")
            args.append(status)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        return list(self.conn.execute(sql, args))

    def _duplicate_candidates(
        self, q_vec: np.ndarray, *, exclude_id: str
    ) -> list[dict[str, Any]]:
        rows = self._load_embeddings()
        out: list[dict[str, Any]] = []
        for r in rows:
            if r["node_id"] == exclude_id:
                continue
            score = cosine(q_vec, _blob_to_vec(r["vector"], r["dim"]))
            if score >= DUPLICATE_THRESHOLD:
                meta = self.conn.execute(
                    "SELECT summary FROM nodes WHERE id = ?", (r["node_id"],)
                ).fetchone()
                out.append({
                    "id": r["node_id"],
                    "summary": meta["summary"] if meta else "",
                    "score": float(score),
                })
        out.sort(key=lambda d: -d["score"])
        return out

    def _step(
        self,
        node_id: str,
        types: list[str] | None,
        direction: str,
    ) -> list[tuple[str, str]]:
        """One hop from `node_id`. Returns (neighbor_id, edge_type) pairs."""
        results: list[tuple[str, str]] = []
        if direction in ("out", "both"):
            sql = "SELECT to_id, type FROM edges WHERE from_id = ?"
            args: list[Any] = [node_id]
            if types is not None:
                sql += f" AND type IN ({','.join('?' * len(types))})"
                args.extend(types)
            results.extend(
                (r["to_id"], r["type"]) for r in self.conn.execute(sql, args)
            )
        if direction in ("in", "both"):
            sql = "SELECT from_id, type FROM edges WHERE to_id = ?"
            args = [node_id]
            if types is not None:
                sql += f" AND type IN ({','.join('?' * len(types))})"
                args.extend(types)
            results.extend(
                (r["from_id"], r["type"]) for r in self.conn.execute(sql, args)
            )
        return results


# -- module helpers ---------------------------------------------------------


def _now_ms() -> int:
    return int(time.time() * 1000)


def _vec_to_blob(vec: np.ndarray) -> bytes:
    return np.ascontiguousarray(vec.astype(np.float32)).tobytes()


def _blob_to_vec(blob: bytes, dim: int) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32, count=dim)


# Silence "unused" warning for asdict imported above; kept for callers that
# want to serialize Note instances to JSON without converting field by field.
_ = asdict
