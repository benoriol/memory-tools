"""Store capture/search/delete behaviour."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from memory_recall.embed import EMBEDDING_DIM, DeterministicFakeEmbedder
from memory_recall.store import Store


class _ControlledEmbedder:
    """Maps known texts to known one-hot vectors. Unknown texts get zeros."""

    dim = EMBEDDING_DIM
    model_name = "controlled"

    def __init__(self, mapping: dict[str, int]) -> None:
        self._mapping = mapping

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            idx = self._mapping.get(t)
            if idx is not None:
                out[i, idx] = 1.0
        return out


def test_capture_inserts_note_and_views(store_root: Path) -> None:
    store = Store(store_root, DeterministicFakeEmbedder())
    note = store.capture(
        "the body",
        title="t",
        summary="a summary line",
        keywords=["kw1", "kw2"],
        paraphrases=["a paraphrase question?"],
    )
    rows = store.conn.execute(
        "SELECT view_kind FROM note_views WHERE note_id = ?", (note.id,)
    ).fetchall()
    kinds = sorted(r["view_kind"] for r in rows)
    assert kinds == ["keyword", "keyword", "paraphrase", "summary"]
    md_path = store_root / "notes" / f"{note.id}.md"
    assert md_path.exists()
    assert "the body" in md_path.read_text()


def test_search_ranks_by_max_pool(store_root: Path) -> None:
    # Three notes, each with a distinct keyword. We use a controlled
    # embedder where dimension i = text marker. The query "needle" matches
    # note B's keyword via the one-hot dimension; B must rank first.
    mapping = {
        "summary-A": 0, "kw-A": 1,
        "summary-B": 2, "kw-B": 3,
        "summary-C": 4, "kw-C": 5,
        "needle": 3,  # matches kw-B exactly
    }
    store = Store(store_root, _ControlledEmbedder(mapping))
    a = store.capture("body-A", title="A", summary="summary-A", keywords=["kw-A"], paraphrases=[])
    b = store.capture("body-B", title="B", summary="summary-B", keywords=["kw-B"], paraphrases=[])
    c = store.capture("body-C", title="C", summary="summary-C", keywords=["kw-C"], paraphrases=[])

    hits = store.search(["needle"], k=3)
    assert hits[0][0].id == b.id
    assert hits[0][2] == "kw-B"
    # The unmatched notes have all-zero similarity (the controlled embedder
    # returns zero vectors for unknown texts), so any order among A/C is OK.
    other_ids = {hits[1][0].id, hits[2][0].id}
    assert other_ids == {a.id, c.id}


def test_search_multi_query_view_max_pool(store_root: Path) -> None:
    mapping = {
        "summary-A": 0, "kw-A": 1,
        "summary-B": 2, "kw-B": 3,
        "q-keyword": 3,
        "q-verbatim": 99,  # matches nothing
    }
    store = Store(store_root, _ControlledEmbedder(mapping))
    store.capture("ba", title="A", summary="summary-A", keywords=["kw-A"], paraphrases=[])
    b = store.capture("bb", title="B", summary="summary-B", keywords=["kw-B"], paraphrases=[])

    # The verbatim query view is zero-aligned with every note, but the
    # keyword view aligns with kw-B; max-pool should still place B first.
    hits = store.search(["q-verbatim", "q-keyword"], k=2)
    assert hits[0][0].id == b.id


def test_delete_removes_note_views_and_file(store_root: Path) -> None:
    store = Store(store_root, DeterministicFakeEmbedder())
    note = store.capture(
        "x", title="t", summary="s", keywords=["k"], paraphrases=["p"]
    )
    md = store_root / "notes" / f"{note.id}.md"
    assert md.exists()
    assert store.delete(note.id) is True
    assert not md.exists()
    rows = store.conn.execute(
        "SELECT COUNT(*) AS n FROM note_views WHERE note_id = ?", (note.id,)
    ).fetchone()["n"]
    assert rows == 0
    assert store.get(note.id) is None


def test_status_counts(store_root: Path) -> None:
    store = Store(store_root, DeterministicFakeEmbedder())
    assert store.status()["count"] == 0
    store.capture("x", title="t", summary="s", keywords=["k"], paraphrases=["p"])
    st = store.status()
    assert st["count"] == 1
    assert st["embedding_dim"] == EMBEDDING_DIM
    assert st["embedding_model"]
