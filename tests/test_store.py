"""End-to-end primitives: capture, get, search, neighbors, link, supersede, status."""

from pathlib import Path

import pytest

from memory_graph.embed import FakeEmbedder
from memory_graph.primitives import Store
from memory_graph.storage import Anchor, Edge
from memory_graph.storage.files import NOTES_DIRNAME


@pytest.fixture()
def s(store: Path) -> Store:
    with Store(store, embedder=FakeEmbedder(dim=32)) as instance:
        yield instance


def _make_kwargs(**over):
    base = dict(
        title="Postgres NOT NULL adds block prod",
        summary="Adding NOT NULL to a >10M-row table holds an exclusive lock.",
        body="Full body of the lesson.",
        kind="lesson",
        tags=["postgres", "migrations"],
    )
    base.update(over)
    return base


# -- capture / get ----------------------------------------------------------


def test_capture_with_short_label_round_trips(s: Store):
    """A short_label written by capture must show up in get() and search()."""
    res = s.capture(
        title="Polynomial degree sweep across noise=0.05/0.20/0.50",
        short_label="polyfit degree sweep",
        summary="degree-3 wins at every noise level",
        body="body",
        kind="experiment",
    )
    note = s.get(res["id"])
    assert note.short_label == "polyfit degree sweep"
    hits = s.search("polyfit degree sweep")
    assert hits and hits[0]["short_label"] == "polyfit degree sweep"


def test_capture_creates_node_markdown_and_embedding(s: Store, store: Path):
    result = s.capture(**_make_kwargs())
    nid = result["id"]
    assert len(nid) == 26  # ULID
    assert result["duplicates"] == []

    # DB row.
    row = s.conn.execute("SELECT * FROM nodes WHERE id = ?", (nid,)).fetchone()
    assert row["title"].startswith("Postgres")
    assert row["status"] == "active"
    assert row["body_hash"] is not None

    # Markdown file.
    md_path = store / NOTES_DIRNAME / f"{nid}.md"
    assert md_path.exists()
    text = md_path.read_text()
    assert "Postgres NOT NULL" in text

    # Embedding.
    erow = s.conn.execute(
        "SELECT * FROM embeddings WHERE node_id = ?", (nid,)
    ).fetchone()
    assert erow is not None
    assert erow["dim"] == 32
    assert len(erow["vector"]) == 32 * 4  # float32 bytes


def test_get_round_trip(s: Store):
    res = s.capture(
        **_make_kwargs(
            anchors=[Anchor(path="src/db.py", pattern="ALTER TABLE")],
        )
    )
    note = s.get(res["id"])
    assert note is not None
    # Tags come back sorted alphabetically.
    assert note.tags == sorted(["postgres", "migrations"])
    assert len(note.anchors) == 1
    assert note.anchors[0].path == "src/db.py"


def test_get_missing_returns_none(s: Store):
    assert s.get("not-a-real-id") is None


def test_capture_dedupes_tags(s: Store):
    res = s.capture(**_make_kwargs(tags=["a", "b", "a", "b", "c"]))
    note = s.get(res["id"])
    assert sorted(note.tags) == ["a", "b", "c"]


# -- search -----------------------------------------------------------------


def test_search_returns_most_similar_first(s: Store):
    """Note whose vocabulary overlaps the query is ranked above the other."""
    relevant = s.capture(
        title="Cursor pagination at high QPS",
        summary="cursor-based pagination at high QPS",
        body="we benchmarked cursor pagination",
        kind="lesson",
    )
    s.capture(
        title="Auth middleware ordering",
        summary="auth middleware ordering decisions",
        body="we picked an ordering for the auth middleware stack",
        kind="lesson",
    )

    hits = s.search("cursor pagination at high QPS", k=2)
    assert hits
    assert hits[0]["id"] == relevant["id"]
    assert hits[0]["score"] > hits[1]["score"]


def test_search_filters_by_kind(s: Store):
    a = s.capture(
        title="alpha", summary="alpha lesson", body="alpha", kind="lesson",
    )
    s.capture(
        title="alpha", summary="alpha capture", body="alpha", kind="capture",
    )

    hits = s.search("alpha lesson", k=10, kind="lesson")
    ids = [h["id"] for h in hits]
    assert a["id"] in ids
    assert all(h["kind"] == "lesson" for h in hits)


def test_search_empty_store_returns_empty(s: Store):
    assert s.search("anything") == []


# -- duplicate detection ----------------------------------------------------


def test_capture_flags_duplicate_when_summary_collides(s: Store):
    first = s.capture(**_make_kwargs(summary="exact duplicate string"))
    # Same content → FakeEmbedder produces identical vector → cosine 1.0.
    second = s.capture(**_make_kwargs(summary="exact duplicate string"))
    assert second["duplicates"], "should flag the first as a duplicate"
    assert second["duplicates"][0]["id"] == first["id"]
    assert second["duplicates"][0]["score"] >= 0.92


def test_capture_does_not_flag_unrelated(s: Store):
    s.capture(**_make_kwargs(summary="alpha alpha alpha"))
    second = s.capture(**_make_kwargs(summary="zeta beta gamma"))
    assert second["duplicates"] == []


# -- batch capture + intra-batch refs --------------------------------------


def test_capture_batch_resolves_placeholders(s: Store):
    # `abstracts: lesson → capture` means the lesson is more abstract;
    # walking outgoing edges from the lesson goes toward concrete evidence.
    results = s.capture_batch([
        {**_make_kwargs(summary="raw observation"), "kind": "observation", "note_id": "@1"},
        {
            **_make_kwargs(summary="distilled lesson"),
            "kind": "principle",
            "note_id": "@2",
            "edges": [{"to": "@1", "type": "abstracts"}],
        },
    ])
    assert len(results) == 2
    cap_id, lesson_id = results[0]["id"], results[1]["id"]
    assert not cap_id.startswith("@")
    assert not lesson_id.startswith("@")

    lesson = s.get(lesson_id)
    assert lesson.edges == [Edge(to_id=cap_id, type="abstracts", weight=1.0)]


def test_capture_batch_accepts_real_ids(s: Store):
    a = s.capture(**_make_kwargs(summary="A"))["id"]
    results = s.capture_batch([
        {
            **_make_kwargs(summary="B"),
            "edges": [{"to": a, "type": "related"}],
        }
    ])
    b = s.get(results[0]["id"])
    assert b.edges[0].to_id == a


# -- neighbors --------------------------------------------------------------


def test_neighbors_depth_one_outgoing(s: Store):
    a = s.capture(**_make_kwargs(summary="A"))["id"]
    b = s.capture(**_make_kwargs(summary="B"))["id"]
    c = s.capture(**_make_kwargs(summary="C"))["id"]
    s.link(a, b, "abstracts")
    s.link(a, c, "related")

    nbrs = s.neighbors(a, depth=1)
    nbr_ids = {n["id"] for n in nbrs}
    assert nbr_ids == {b, c}
    by_id = {n["id"]: n for n in nbrs}
    assert by_id[b]["edge_type"] == "abstracts"
    assert by_id[c]["edge_type"] == "related"


def test_neighbors_filters_by_edge_type(s: Store):
    a = s.capture(**_make_kwargs(summary="A"))["id"]
    b = s.capture(**_make_kwargs(summary="B"))["id"]
    c = s.capture(**_make_kwargs(summary="C"))["id"]
    s.link(a, b, "abstracts")
    s.link(a, c, "related")

    nbrs = s.neighbors(a, types=["abstracts"], depth=1)
    assert [n["id"] for n in nbrs] == [b]


def test_neighbors_depth_two(s: Store):
    a = s.capture(**_make_kwargs(summary="A"))["id"]
    b = s.capture(**_make_kwargs(summary="B"))["id"]
    c = s.capture(**_make_kwargs(summary="C"))["id"]
    s.link(a, b, "related")
    s.link(b, c, "related")

    one_hop = s.neighbors(a, depth=1)
    two_hop = s.neighbors(a, depth=2)
    assert [n["id"] for n in one_hop] == [b]
    assert {n["id"] for n in two_hop} == {b, c}
    by_id = {n["id"]: n for n in two_hop}
    assert by_id[b]["distance"] == 1
    assert by_id[c]["distance"] == 2


def test_neighbors_both_directions(s: Store):
    a = s.capture(**_make_kwargs(summary="A"))["id"]
    b = s.capture(**_make_kwargs(summary="B"))["id"]
    s.link(b, a, "supersedes")

    out_only = s.neighbors(a, depth=1, direction="out")
    in_only = s.neighbors(a, depth=1, direction="in")
    both = s.neighbors(a, depth=1, direction="both")
    assert out_only == []
    assert [n["id"] for n in in_only] == [b]
    assert [n["id"] for n in both] == [b]


# -- link / unlink / supersede / mark --------------------------------------


def test_link_is_idempotent(s: Store):
    a = s.capture(**_make_kwargs(summary="A"))["id"]
    b = s.capture(**_make_kwargs(summary="B"))["id"]
    s.link(a, b, "related")
    s.link(a, b, "related", weight=2.5)  # overwrites
    row = s.conn.execute(
        "SELECT weight FROM edges WHERE from_id = ? AND to_id = ? AND type = ?",
        (a, b, "related"),
    ).fetchone()
    assert row["weight"] == 2.5


def test_unlink_removes_edge(s: Store):
    a = s.capture(**_make_kwargs(summary="A"))["id"]
    b = s.capture(**_make_kwargs(summary="B"))["id"]
    s.link(a, b, "related")
    s.unlink(a, b, "related")
    assert s.conn.execute("SELECT COUNT(*) AS n FROM edges").fetchone()["n"] == 0


def test_supersede_marks_old_and_links(s: Store):
    old = s.capture(**_make_kwargs(summary="old"))["id"]
    new = s.capture(**_make_kwargs(summary="new"))["id"]
    s.supersede(old_id=old, new_id=new, reason="replaced by clearer wording")

    old_note = s.get(old)
    assert old_note.status == "superseded"
    new_note = s.get(new)
    assert any(e.to_id == old and e.type == "supersedes" for e in new_note.edges)


def test_mark_changes_status(s: Store):
    a = s.capture(**_make_kwargs(summary="A"))["id"]
    s.mark(a, "disputed")
    assert s.get(a).status == "disputed"


# -- status -----------------------------------------------------------------


def test_status_counts(s: Store):
    s.capture(**_make_kwargs(kind="lesson", summary="alpha"))
    s.capture(**_make_kwargs(kind="lesson", summary="beta"))
    s.capture(**_make_kwargs(kind="experiment", summary="gamma"))
    a = s.capture(**_make_kwargs(kind="capture", summary="delta"))["id"]
    b = s.capture(**_make_kwargs(kind="capture", summary="epsilon"))["id"]
    s.link(a, b, "related")

    status = s.status()
    assert status["total_nodes"] == 5
    assert status["total_edges"] == 1
    assert status["by_kind"]["lesson"] == 2
    assert status["by_kind"]["experiment"] == 1
    assert status["by_kind"]["capture"] == 2
    assert status["by_edge_type"]["related"] == 1
    assert status["embedding_dim"] == 32
    assert status["embedding_model"] == "fake"
