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


def test_install_claude_md_creates_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["install-claude-md"])
    assert rc == 0
    text = (tmp_path / "CLAUDE.md").read_text()
    assert "<!-- BEGIN memory-recall -->" in text
    assert "<!-- END memory-recall -->" in text
    assert "Long-term memory" in text


def test_install_claude_md_appends_to_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# project rules\n\nsome content\n")
    rc = main(["install-claude-md"])
    assert rc == 0
    text = (tmp_path / "CLAUDE.md").read_text()
    assert text.startswith("# project rules\n\nsome content\n")
    assert "<!-- BEGIN memory-recall -->" in text
    assert text.endswith("<!-- END memory-recall -->\n")


def test_install_claude_md_idempotency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["install-claude-md"]) == 0
    # Re-run without --force returns 1.
    assert main(["install-claude-md"]) == 1
    # With --force replaces (count stays at one).
    assert main(["install-claude-md", "--force"]) == 0
    text = (tmp_path / "CLAUDE.md").read_text()
    assert text.count("<!-- BEGIN memory-recall -->") == 1
    assert text.count("<!-- END memory-recall -->") == 1


def test_install_claude_md_force_replaces_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "CLAUDE.md").write_text(
        "# rules\n\n<!-- BEGIN memory-recall -->\nOLD CONTENT\n<!-- END memory-recall -->\n\nafter\n"
    )
    rc = main(["install-claude-md", "--force"])
    assert rc == 0
    text = (tmp_path / "CLAUDE.md").read_text()
    assert "OLD CONTENT" not in text
    assert "# rules" in text
    assert "after" in text
    assert text.count("<!-- BEGIN memory-recall -->") == 1


def test_uninstall_claude_md_removes_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "CLAUDE.md").write_text(
        "# rules\n\n<!-- BEGIN memory-recall -->\nbody\n<!-- END memory-recall -->\n\nafter\n"
    )
    rc = main(["uninstall-claude-md"])
    assert rc == 0
    text = (tmp_path / "CLAUDE.md").read_text()
    assert "memory-recall" not in text
    assert "# rules" in text
    assert "after" in text


def test_uninstall_claude_md_no_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# just rules\n")
    rc = main(["uninstall-claude-md"])
    assert rc == 0
    assert (tmp_path / "CLAUDE.md").read_text() == "# just rules\n"


def test_uninstall_claude_md_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["uninstall-claude-md"])
    assert rc == 0


def test_setup_fresh_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["setup"])
    assert rc == 0
    assert (tmp_path / ".mcp.json").exists()
    assert (tmp_path / ".memory-recall" / "notes").is_dir()
    text = (tmp_path / "CLAUDE.md").read_text()
    assert "<!-- BEGIN memory-recall -->" in text


def test_setup_idempotent_rerun(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["setup"]) == 0
    # Re-run on fully set-up project still exits 0.
    assert main(["setup"]) == 0
    text = (tmp_path / "CLAUDE.md").read_text()
    assert text.count("<!-- BEGIN memory-recall -->") == 1


def test_setup_skip_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["setup", "--skip-register", "--skip-claude-md"])
    assert rc == 0
    assert not (tmp_path / ".mcp.json").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".memory-recall" / "notes").is_dir()


def test_setup_force_replaces_claude_md(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "CLAUDE.md").write_text(
        "<!-- BEGIN memory-recall -->\nOLD\n<!-- END memory-recall -->\n"
    )
    rc = main(["setup", "--force"])
    assert rc == 0
    text = (tmp_path / "CLAUDE.md").read_text()
    assert "OLD" not in text
    assert "Long-term memory" in text
