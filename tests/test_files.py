"""Markdown-with-frontmatter round-trip."""

from pathlib import Path

import pytest

from memory_graph.storage import Anchor, Edge, Note, new_id, read_note, store_root, write_note
from memory_graph.storage.files import NOTES_DIRNAME, STORE_DIRNAME


def _make_note(**overrides) -> Note:
    defaults = dict(
        id=new_id(),
        title="Migration 0042 blocked prod",
        short_label="0042 lock incident",
        summary="NOT NULL adds on >10M-row tables lock writes.",
        body="Full body of the note.\n\nSecond paragraph.",
        kind="lesson",
        status="validated",
        created_at=1_700_000_000_000,
        updated_at=1_700_000_001_000,
        tags=["postgres", "migrations"],
        edges=[Edge(to_id="ABCDEF", type="derived_from")],
        anchors=[Anchor(path="src/db.py", pattern="ALTER TABLE", commit_sha="abc123")],
    )
    defaults.update(overrides)
    return Note(**defaults)


def test_write_then_read_roundtrip(store: Path):
    original = _make_note()
    path = write_note(store, original)
    assert path.exists()
    assert path.parent.name == NOTES_DIRNAME

    loaded = read_note(path)
    # The body and frontmatter survive intact.
    assert loaded.id == original.id
    assert loaded.title == original.title
    assert loaded.short_label == original.short_label
    assert loaded.summary == original.summary
    assert loaded.body == original.body
    assert loaded.kind == original.kind
    assert loaded.status == original.status
    assert loaded.created_at == original.created_at
    assert loaded.updated_at == original.updated_at
    assert loaded.tags == original.tags
    assert len(loaded.edges) == 1
    assert loaded.edges[0].to_id == "ABCDEF"
    assert loaded.edges[0].type == "derived_from"
    assert loaded.anchors[0].path == "src/db.py"
    assert loaded.anchors[0].pattern == "ALTER TABLE"
    assert loaded.anchors[0].commit_sha == "abc123"


def test_note_without_optional_fields(store: Path):
    note = Note(
        id=new_id(),
        title="bare",
        summary="bare summary",
        body="bare body",
        kind="capture",
        created_at=1,
        updated_at=2,
    )
    path = write_note(store, note)
    loaded = read_note(path)
    assert loaded.tags == []
    assert loaded.edges == []
    assert loaded.anchors == []
    assert loaded.happened_at is None
    assert loaded.last_verified_at is None
    # Notes without a short_label round-trip as None (and the viz falls
    # back to the title).
    assert loaded.short_label is None


def test_eventive_timestamps_preserved(store: Path):
    note = _make_note(happened_at=1_600_000_000_000, last_verified_at=None)
    path = write_note(store, note)
    loaded = read_note(path)
    assert loaded.happened_at == 1_600_000_000_000
    assert loaded.last_verified_at is None


def test_store_root_walks_up(tmp_path: Path):
    project = tmp_path / "project"
    nested = project / "src" / "deep" / "subdir"
    nested.mkdir(parents=True)
    (project / STORE_DIRNAME).mkdir()
    assert store_root(nested) == project / STORE_DIRNAME


def test_store_root_errors_when_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        store_root(tmp_path)


def test_read_note_rejects_missing_frontmatter(tmp_path: Path):
    path = tmp_path / "bad.md"
    path.write_text("no frontmatter here\n")
    with pytest.raises(ValueError):
        read_note(path)
