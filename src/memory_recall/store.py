"""Multi-vector store: SQLite + markdown for memory notes."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import numpy as np

from memory_recall.embed import Embedder
from memory_recall.storage.db import connect, pack_embedding, unpack_embedding
from memory_recall.storage.files import note_md_path, notes_dir
from memory_recall.storage.ids import new_id
from memory_recall.storage.note import Note, NoteView


def _normalize(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return matrix
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms > 0, norms, 1.0)
    return matrix / norms


def _frontmatter(note: Note) -> str:
    lines = [
        "---",
        f"id: {note.id}",
        f"title: {_yaml_escape(note.title)}",
        f"summary: {_yaml_escape(note.summary)}",
        f"tags: {json.dumps(note.tags)}",
        f"created_at: {note.created_at}",
        f"updated_at: {note.updated_at}",
        "---",
        "",
    ]
    return "\n".join(lines)


def _yaml_escape(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


class Store:
    """Multi-vector note store backed by SQLite + markdown."""

    def __init__(self, root: Path, embedder: Embedder) -> None:
        self.root = root
        self.embedder = embedder
        self.conn: sqlite3.Connection = connect(root)

    def close(self) -> None:
        self.conn.close()

    def capture(
        self,
        content: str,
        *,
        title: str,
        summary: str,
        keywords: list[str],
        paraphrases: list[str],
        tags: list[str] | None = None,
    ) -> Note:
        """Insert a new note plus one embedded view per (summary, keyword, paraphrase)."""
        now = int(time.time() * 1000)
        note = Note(
            id=new_id(now),
            title=title,
            summary=summary,
            body=content,
            tags=list(tags or []),
            created_at=now,
            updated_at=now,
        )

        views: list[tuple[str, str]] = [("summary", summary)]
        for kw in keywords:
            if kw.strip():
                views.append(("keyword", kw.strip()))
        for ph in paraphrases:
            if ph.strip():
                views.append(("paraphrase", ph.strip()))

        texts = [v[1] for v in views]
        embeddings = self.embedder.embed(texts)

        with self.conn:
            self.conn.execute(
                "INSERT INTO notes (id, title, summary, body, tags, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    note.id,
                    note.title,
                    note.summary,
                    note.body,
                    json.dumps(note.tags),
                    note.created_at,
                    note.updated_at,
                ),
            )
            self.conn.executemany(
                "INSERT INTO note_views (note_id, view_kind, view_text, embedding) "
                "VALUES (?, ?, ?, ?)",
                [
                    (note.id, kind, text, pack_embedding(emb))
                    for (kind, text), emb in zip(views, embeddings, strict=True)
                ],
            )

        md_path = note_md_path(self.root, note.id)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_frontmatter(note) + content + "\n")
        return note

    def search(
        self, query_views: list[str], k: int = 10
    ) -> list[tuple[Note, float, str]]:
        """Embed each query view, max-pool cosine similarity per note, return top-k."""
        if not query_views:
            return []
        q = _normalize(self.embedder.embed(query_views))

        rows = self.conn.execute(
            "SELECT note_id, view_text, embedding FROM note_views"
        ).fetchall()
        if not rows:
            return []

        mats: list[np.ndarray] = []
        note_ids: list[str] = []
        view_texts: list[str] = []
        for r in rows:
            mats.append(unpack_embedding(r["embedding"]))
            note_ids.append(r["note_id"])
            view_texts.append(r["view_text"])
        view_mat = _normalize(np.vstack(mats))

        # (Q, D) @ (D, V) -> (Q, V); max over Q gives best query-view per stored view.
        sim_qv = q @ view_mat.T
        per_view = sim_qv.max(axis=0)

        # max-pool per note + remember the winning view
        best: dict[str, tuple[float, str]] = {}
        for nid, score, text in zip(note_ids, per_view.tolist(), view_texts, strict=True):
            cur = best.get(nid)
            if cur is None or score > cur[0]:
                best[nid] = (float(score), text)

        ranked = sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)[:k]
        out: list[tuple[Note, float, str]] = []
        for nid, (score, text) in ranked:
            note = self.get(nid)
            if note is not None:
                out.append((note, score, text))
        return out

    def get(self, note_id: str) -> Note | None:
        row = self.conn.execute(
            "SELECT * FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        return _row_to_note(row) if row else None

    def get_views(self, note_id: str) -> list[NoteView]:
        rows = self.conn.execute(
            "SELECT id, note_id, view_kind, view_text, embedding FROM note_views "
            "WHERE note_id = ? ORDER BY id",
            (note_id,),
        ).fetchall()
        return [
            NoteView(
                id=r["id"],
                note_id=r["note_id"],
                view_kind=r["view_kind"],
                view_text=r["view_text"],
                embedding=unpack_embedding(r["embedding"]),
            )
            for r in rows
        ]

    def list_notes(self, limit: int = 100, offset: int = 0) -> list[Note]:
        rows = self.conn.execute(
            "SELECT * FROM notes ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [_row_to_note(r) for r in rows]

    def delete(self, note_id: str) -> bool:
        with self.conn:
            cur = self.conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            removed = cur.rowcount > 0
            self.conn.execute("DELETE FROM note_views WHERE note_id = ?", (note_id,))
        if removed:
            p = note_md_path(self.root, note_id)
            if p.exists():
                p.unlink()
        return removed

    def status(self) -> dict[str, Any]:
        count = self.conn.execute("SELECT COUNT(*) AS n FROM notes").fetchone()["n"]
        last = self.conn.execute(
            "SELECT MAX(created_at) AS t FROM notes"
        ).fetchone()["t"]
        return {
            "count": count,
            "embedding_model": self.embedder.model_name,
            "embedding_dim": self.embedder.dim,
            "last_created_at": last,
            "notes_dir": str(notes_dir(self.root)),
        }


def _row_to_note(row: sqlite3.Row) -> Note:
    return Note(
        id=row["id"],
        title=row["title"],
        summary=row["summary"],
        body=row["body"],
        tags=json.loads(row["tags"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
