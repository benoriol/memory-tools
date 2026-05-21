"""CLI smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from memory_recall.cli import main


def test_init_creates_directory(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["init", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / ".memory-recall" / "notes").is_dir()
    assert (tmp_path / ".memory-recall" / "config.yml").exists()


def test_status_outputs_json(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # status uses store_root() which walks up from cwd.
    monkeypatch.chdir(tmp_path)
    main(["init"])
    capsys.readouterr()  # clear

    # Swap in fake embedder before status (avoids loading FastEmbed).
    from memory_recall import cli, embed

    monkeypatch.setattr(embed, "LocalEmbedder", embed.DeterministicFakeEmbedder)
    monkeypatch.setattr(cli, "store_root", lambda: tmp_path / ".memory-recall")

    rc = main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["count"] == 0
    assert data["embedding_dim"] == 384


def test_register_writes_mcp_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["register"])
    assert rc == 0
    cfg = json.loads((tmp_path / ".mcp.json").read_text())
    assert cfg["mcpServers"]["memory-recall"]["command"] == "memory-recall"
    assert cfg["mcpServers"]["memory-recall"]["args"] == ["serve"]


def test_register_idempotency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["register"]) == 0
    # Second call without --force returns 1.
    assert main(["register"]) == 1
    # With --force should succeed.
    assert main(["register", "--force"]) == 0


def test_unregister_removes_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".mcp.json").write_text(json.dumps({
        "mcpServers": {
            "other": {"command": "x"},
            "memory-recall": {"command": "memory-recall", "args": ["serve"]},
        }
    }))
    assert main(["unregister"]) == 0
    cfg = json.loads((tmp_path / ".mcp.json").read_text())
    assert "memory-recall" not in cfg["mcpServers"]
    assert "other" in cfg["mcpServers"]
