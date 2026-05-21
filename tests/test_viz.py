"""Visualization FastAPI app tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from memory_recall import subagent as subagent_module
from memory_recall.embed import DeterministicFakeEmbedder
from memory_recall.store import Store
from memory_recall.viz.app import create_app


@pytest.fixture()
def client(store_root: Path):
    store = Store(store_root, DeterministicFakeEmbedder())
    store.capture("body one", title="One", summary="First note", keywords=["k"], paraphrases=["p"])
    store.capture("body two", title="Two", summary="Second note", keywords=["k2"], paraphrases=["p2"])
    app = create_app(store=store)
    return TestClient(app), store


def test_list_notes(client) -> None:
    c, _ = client
    r = c.get("/api/notes")
    assert r.status_code == 200
    data = r.json()
    assert len(data["notes"]) == 2
    for n in data["notes"]:
        assert "embedding_2d" in n
        assert len(n["embedding_2d"]) == 2


def test_get_note_returns_views(client) -> None:
    c, store = client
    nid = store.list_notes()[0].id
    r = c.get(f"/api/notes/{nid}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == nid
    kinds = sorted(v["kind"] for v in data["views"])
    assert "summary" in kinds


def test_get_note_404(client) -> None:
    c, _ = client
    r = c.get("/api/notes/does-not-exist")
    assert r.status_code == 404


def test_search(client, monkeypatch: pytest.MonkeyPatch) -> None:
    c, store = client

    target_summary = store.list_notes()[-1].summary  # oldest is last

    async def fake_search(query: str, *, model=None):
        return {
            "keywords": [target_summary],
            "paraphrases": [],
            "query_views": [query, target_summary],
        }

    # Patch the import inside viz.app's namespace (it imported the symbol).
    from memory_recall.viz import app as viz_app

    monkeypatch.setattr(viz_app, "expand_for_search", fake_search)

    r = c.post("/api/search", json={"query": "anything", "k": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["expanded"]["keywords"] == [target_summary]
    assert data["results"]
    assert data["results"][0]["score"] >= data["results"][-1]["score"]


def test_delete_note(client) -> None:
    c, store = client
    nid = store.list_notes()[0].id
    r = c.delete(f"/api/notes/{nid}")
    assert r.status_code == 200
    assert c.get(f"/api/notes/{nid}").status_code == 404
