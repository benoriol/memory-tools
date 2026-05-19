"""CLI subcommands: init, status, reindex."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory_graph.cli import main as cli_main
from memory_graph.embed import FakeEmbedder
from memory_graph.primitives import Store
from memory_graph.storage import Edge, new_id, write_note
from memory_graph.storage.files import NOTES_DIRNAME, STORE_DIRNAME
from memory_graph.storage.note import Note


def _seed_note(store: Path, **fields):
    note = Note(
        id=new_id(),
        title=fields.get("title", "t"),
        summary=fields.get("summary", "s"),
        body=fields.get("body", "b"),
        kind=fields.get("kind", "capture"),
        status=fields.get("status", "active"),
        created_at=1, updated_at=1,
        tags=fields.get("tags", []),
        edges=fields.get("edges", []),
    )
    write_note(store, note)
    return note


# -- init -------------------------------------------------------------------


def test_init_creates_directories(tmp_path: Path, capsys: pytest.CaptureFixture):
    code = cli_main(["init", "--path", str(tmp_path)])
    assert code == 0
    root = tmp_path / STORE_DIRNAME
    assert (root / NOTES_DIRNAME).is_dir()
    assert (root / "_operator").is_dir()
    assert (root / "_pending").is_dir()
    assert (root / "config.yml").exists()
    out = capsys.readouterr().out
    assert "Initialized" in out


def test_init_refuses_existing(tmp_path: Path, capsys: pytest.CaptureFixture):
    (tmp_path / STORE_DIRNAME).mkdir()
    code = cli_main(["init", "--path", str(tmp_path)])
    assert code == 1
    err = capsys.readouterr().err
    assert "Already initialized" in err


# -- status -----------------------------------------------------------------


def test_status_prints_json(tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch):
    cli_main(["init", "--path", str(tmp_path)])
    capsys.readouterr()  # drop init's output

    # Seed via Store + FakeEmbedder so we don't hit FastEmbed.
    root = tmp_path / STORE_DIRNAME
    with Store(root, embedder=FakeEmbedder()) as s:
        s.capture(title="t", summary="s", body="b", kind="lesson")

    # Patch LocalEmbedder so we don't download the real model.
    import memory_graph.embed as embed_mod

    monkeypatch.setattr(embed_mod, "LocalEmbedder", lambda *a, **k: FakeEmbedder())

    code = cli_main(["status", "--path", str(tmp_path)])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["total_nodes"] == 1
    assert data["by_kind"]["lesson"] == 1


# -- reindex ----------------------------------------------------------------


def test_reindex_rebuilds_from_markdown(tmp_path: Path, monkeypatch, capsys):
    cli_main(["init", "--path", str(tmp_path)])
    capsys.readouterr()

    root = tmp_path / STORE_DIRNAME
    # Write two markdown notes directly (simulating a git pull / manual edit).
    a = _seed_note(root, title="alpha", summary="alpha", body="alpha")
    b = _seed_note(
        root, title="beta", summary="beta", body="beta",
        edges=[Edge(to_id=a.id, type="related")],
    )

    # Patch LocalEmbedder to avoid the model download in reindex.
    import memory_graph.embed as embed_mod

    monkeypatch.setattr(embed_mod, "LocalEmbedder", lambda *a, **k: FakeEmbedder())

    code = cli_main(["reindex", "--path", str(tmp_path)])
    assert code == 0

    # Confirm both notes are now in the DB.
    with Store(root, embedder=FakeEmbedder()) as s:
        got_a = s.get(a.id)
        got_b = s.get(b.id)
        assert got_a is not None and got_a.title == "alpha"
        assert got_b is not None
        assert any(e.to_id == a.id for e in got_b.edges)


def test_reindex_errors_when_no_notes_dir(tmp_path: Path, capsys):
    (tmp_path / STORE_DIRNAME).mkdir()
    # Don't create notes/ subdir.
    code = cli_main(["reindex", "--path", str(tmp_path)])
    assert code == 1
    err = capsys.readouterr().err
    assert "no notes directory" in err


# -- digest -----------------------------------------------------------------


def test_digest_errors_without_transcript(capsys, monkeypatch, tmp_path):
    monkeypatch.delenv("CLAUDE_TRANSCRIPT_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / STORE_DIRNAME).mkdir()
    code = cli_main(["digest"])
    assert code == 2
    err = capsys.readouterr().err
    assert "no transcript" in err


def test_digest_skips_empty_transcript(tmp_path: Path, capsys, monkeypatch):
    cli_main(["init", "--path", str(tmp_path)])
    capsys.readouterr()
    monkeypatch.chdir(tmp_path)
    transcript = tmp_path / "empty.txt"
    transcript.write_text("\n")
    code = cli_main(["digest", "--transcript", str(transcript)])
    assert code == 0
    err = capsys.readouterr().err
    assert "empty" in err


# -- help and parser smoke --------------------------------------------------


def test_cli_help_runs(capsys):
    with pytest.raises(SystemExit) as exc:
        cli_main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for cmd in ("init", "serve", "digest", "reindex", "status"):
        assert cmd in out
