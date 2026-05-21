"""FastAPI app: notes browser + sub-agent search."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from memory_recall.embed import Embedder, LocalEmbedder
from memory_recall.storage.files import store_root
from memory_recall.store import Store
from memory_recall.subagent import expand_for_search


class _Projection:
    """Cached 2D PCA over summary embeddings.

    The PCA basis (centroid + 2 principal components) is recomputed only
    after `recompute_after` new notes have been captured since the last
    basis fit. In between, newly added notes are *projected onto the
    existing basis* and cached, so per-request work is proportional only
    to the number of unseen notes — not the whole store.
    """

    def __init__(self, recompute_after: int = 10) -> None:
        self.recompute_after = recompute_after
        self._basis: np.ndarray | None = None       # shape (2, D)
        self._centroid: np.ndarray | None = None    # shape (D,)
        self._fitted_count: int = 0
        self._xy: dict[str, tuple[float, float]] = {}

    def get(self, store: Store) -> dict[str, tuple[float, float]]:
        from memory_recall.storage.db import unpack_embedding

        rows = store.conn.execute(
            "SELECT note_id, embedding FROM note_views WHERE view_kind = 'summary'"
        ).fetchall()
        n = len(rows)
        if n == 0:
            self._reset()
            return self._xy

        unseen = [r for r in rows if r["note_id"] not in self._xy]
        need_refit = (
            self._basis is None
            or n - self._fitted_count >= self.recompute_after
            or len(unseen) > self.recompute_after
        )

        if need_refit:
            ids = [r["note_id"] for r in rows]
            mat = np.vstack([unpack_embedding(r["embedding"]) for r in rows])
            self._centroid = mat.mean(axis=0)
            centered = mat - self._centroid
            if n == 1:
                self._basis = np.zeros((2, mat.shape[1]), dtype=np.float32)
                xy = np.zeros((1, 2), dtype=np.float32)
            else:
                _, _, vt = np.linalg.svd(centered, full_matrices=False)
                self._basis = vt[:2]
                xy = centered @ self._basis.T
            self._xy = {nid: (float(xy[i, 0]), float(xy[i, 1])) for i, nid in enumerate(ids)}
            self._fitted_count = n
            return self._xy

        # Incremental: project only the new notes onto the existing basis.
        if unseen:
            assert self._basis is not None and self._centroid is not None
            mat = np.vstack([unpack_embedding(r["embedding"]) for r in unseen])
            xy = (mat - self._centroid) @ self._basis.T
            for i, r in enumerate(unseen):
                self._xy[r["note_id"]] = (float(xy[i, 0]), float(xy[i, 1]))
        return self._xy

    def _reset(self) -> None:
        self._basis = None
        self._centroid = None
        self._fitted_count = 0
        self._xy = {}


class SearchBody(BaseModel):
    query: str
    k: int = 10


def create_app(
    *, store: Store | None = None, embedder: Embedder | None = None
) -> FastAPI:
    """FastAPI factory. Pass `store` for tests; defaults to disk-discovered."""
    app = FastAPI(title="memory-recall viz")
    _proj = _Projection()

    def _store() -> Store:
        if store is not None:
            return store
        if not hasattr(app.state, "store"):
            emb = embedder or LocalEmbedder()
            app.state.store = Store(store_root(), emb)
        return app.state.store

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        html = resources.files("memory_recall.viz.static").joinpath("index.html").read_text()
        return html

    @app.get("/api/notes")
    def list_notes() -> dict[str, Any]:
        s = _store()
        notes = s.list_notes(limit=10_000)
        xy = _proj.get(s)
        return {
            "notes": [
                {
                    "id": n.id,
                    "title": n.title,
                    "summary": n.summary,
                    "tags": n.tags,
                    "created_at": n.created_at,
                    "embedding_2d": list(xy.get(n.id, (0.0, 0.0))),
                }
                for n in notes
            ]
        }

    @app.get("/api/notes/{note_id}")
    def get_note(note_id: str) -> dict[str, Any]:
        s = _store()
        n = s.get(note_id)
        if n is None:
            raise HTTPException(status_code=404, detail="not found")
        views = s.get_views(note_id)
        return {
            **n.to_dict(),
            "views": [
                {"kind": v.view_kind, "text": v.view_text} for v in views
            ],
        }

    @app.delete("/api/notes/{note_id}")
    def delete_note(note_id: str) -> dict[str, Any]:
        s = _store()
        ok = s.delete(note_id)
        if not ok:
            raise HTTPException(status_code=404, detail="not found")
        return {"deleted": note_id}

    @app.post("/api/search")
    async def search(body: SearchBody) -> dict[str, Any]:
        s = _store()
        expanded = await expand_for_search(body.query)
        hits = s.search(expanded["query_views"], k=body.k)
        return {
            "query": body.query,
            "expanded": {
                "keywords": expanded["keywords"],
                "paraphrases": expanded["paraphrases"],
                "query_views": expanded["query_views"],
            },
            "results": [
                {
                    "id": n.id,
                    "title": n.title,
                    "summary": n.summary,
                    "tags": n.tags,
                    "score": round(score, 4),
                    "matched_view": matched,
                }
                for (n, score, matched) in hits
            ],
        }

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return _store().status()

    return app


__all__ = ["create_app"]
