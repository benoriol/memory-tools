"""Detect / install / update / remove the memory protocol in CLAUDE.md."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory_graph.claude_md import (
    END_MARKER,
    START_MARKER,
    extract_protocol_block,
    find_target,
    has_protocol,
    install,
    template_text,
    uninstall,
)
from memory_graph.cli import main as cli_main


# -- low-level helpers ------------------------------------------------------


def test_template_is_packaged_and_wraps_with_sentinels():
    txt = template_text()
    assert START_MARKER in txt
    assert END_MARKER in txt
    # The visible section header is present so users see it in their CLAUDE.md.
    assert "## Memory protocol" in txt


def test_extract_protocol_block_finds_sentinels():
    body = (
        "# Project\n\nSome existing content.\n\n"
        + START_MARKER
        + " -->\nfoo\n"
        + END_MARKER
        + "\n\ntrailing\n"
    )
    region = extract_protocol_block(body)
    assert region is not None
    s, e = region
    assert body[s:e].startswith(START_MARKER)
    assert body[s:e].rstrip().endswith(END_MARKER)


def test_extract_protocol_block_missing_returns_none():
    assert extract_protocol_block("# nothing here\n") is None
    # Half-present (start only) → still None.
    assert extract_protocol_block("# nope\n" + START_MARKER + " -->\n") is None


def test_has_protocol():
    assert has_protocol(template_text())
    assert not has_protocol("# unrelated content\n")


def test_find_target_root_claude_md(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("hi\n")
    assert find_target(tmp_path) == f


def test_find_target_fallback_dotclaude(tmp_path: Path):
    (tmp_path / ".claude").mkdir()
    f = tmp_path / ".claude" / "CLAUDE.md"
    f.write_text("hi\n")
    assert find_target(tmp_path) == f


def test_find_target_returns_none_when_missing(tmp_path: Path):
    assert find_target(tmp_path) is None


# -- install ---------------------------------------------------------------


def test_install_into_existing_file_appends(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    original = "# Project\n\nExisting body.\n"
    f.write_text(original)
    status, _ = install(f)
    assert status == "installed"
    new = f.read_text()
    # Original content is preserved at the top.
    assert new.startswith(original)
    # Protocol block is at the bottom.
    assert has_protocol(new)
    assert new.rstrip().endswith(END_MARKER)


def test_install_into_empty_file(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("")
    status, _ = install(f)
    assert status == "installed"
    assert has_protocol(f.read_text())


def test_install_is_idempotent_when_template_matches(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("# X\n\n")
    install(f)
    status, _ = install(f)
    assert status == "unchanged"


def test_install_refuses_when_existing_section_differs_without_force(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    # Drop in a stale version of the protocol (sentinels present, body different).
    f.write_text(
        "# X\n\n"
        + START_MARKER
        + " -->\n## Memory protocol\nold version stuff\n"
        + END_MARKER
        + "\n"
    )
    status, msg = install(f)
    assert status == "stale"
    assert "force" in msg.lower()


def test_install_force_replaces_existing_section(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    stale_body = (
        "# X\n\n"
        + START_MARKER
        + " -->\n## Memory protocol\nold version stuff\n"
        + END_MARKER
        + "\n\nafter section\n"
    )
    f.write_text(stale_body)
    status, _ = install(f, force=True)
    assert status == "replaced"
    new = f.read_text()
    # New content has the template body.
    assert "memory_remember" in new
    # Content surrounding the block survived.
    assert "after section" in new
    assert new.startswith("# X")


def test_install_preserves_separation_when_appending(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("# X\n\nbody\nno trailing newline")
    install(f)
    text = f.read_text()
    # There must be at least one blank line between prior content and the
    # appended block (so the markdown renderer doesn't merge them).
    assert "no trailing newline\n\n" + START_MARKER in text


# -- uninstall --------------------------------------------------------------


def test_uninstall_removes_block_and_tidies(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    install(f.parent / "CLAUDE.md") if False else None  # no-op clarity
    f.write_text("# X\n\nbody\n")
    install(f)
    status, _ = uninstall(f)
    assert status == "removed"
    text = f.read_text()
    assert not has_protocol(text)
    # And we don't leave 3+ consecutive newlines lying around.
    assert "\n\n\n" not in text


def test_uninstall_absent_section_is_a_noop(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("# X\n\nbody\n")
    status, _ = uninstall(f)
    assert status == "absent"
    # File is unchanged.
    assert f.read_text() == "# X\n\nbody\n"


def test_uninstall_missing_file(tmp_path: Path):
    status, _ = uninstall(tmp_path / "no-such-file.md")
    assert status == "missing"


# -- CLI surface -----------------------------------------------------------


def test_cli_install_creates_file_with_create_flag(tmp_path: Path, capsys):
    code = cli_main(["install-claude-md", "--path", str(tmp_path), "--create"])
    assert code == 0
    assert (tmp_path / "CLAUDE.md").exists()
    assert has_protocol((tmp_path / "CLAUDE.md").read_text())


def test_cli_install_errors_when_target_missing_without_create(tmp_path: Path, capsys):
    code = cli_main(["install-claude-md", "--path", str(tmp_path)])
    assert code == 1
    err = capsys.readouterr().err
    assert "no CLAUDE.md found" in err


def test_cli_install_into_existing_root_claude_md(tmp_path: Path, capsys):
    (tmp_path / "CLAUDE.md").write_text("# Project\n\nDescription.\n")
    code = cli_main(["install-claude-md", "--path", str(tmp_path)])
    assert code == 0
    out = capsys.readouterr().out
    assert "appended" in out
    text = (tmp_path / "CLAUDE.md").read_text()
    assert text.startswith("# Project\n\nDescription.\n")
    assert "memory_remember" in text


def test_cli_install_is_idempotent(tmp_path: Path, capsys):
    (tmp_path / "CLAUDE.md").write_text("# X\n")
    cli_main(["install-claude-md", "--path", str(tmp_path)])
    capsys.readouterr()
    code = cli_main(["install-claude-md", "--path", str(tmp_path)])
    assert code == 0
    out = capsys.readouterr().out
    assert "already current" in out


def test_cli_install_stale_without_force_returns_2(tmp_path: Path, capsys):
    (tmp_path / "CLAUDE.md").write_text(
        "# X\n\n" + START_MARKER + " -->\nold body\n" + END_MARKER + "\n"
    )
    code = cli_main(["install-claude-md", "--path", str(tmp_path)])
    assert code == 2
    err = capsys.readouterr().err
    assert "force" in err.lower()


def test_cli_install_force_replaces(tmp_path: Path, capsys):
    (tmp_path / "CLAUDE.md").write_text(
        "# X\n\n" + START_MARKER + " -->\nold body\n" + END_MARKER + "\n"
    )
    code = cli_main(["install-claude-md", "--path", str(tmp_path), "--force"])
    assert code == 0
    text = (tmp_path / "CLAUDE.md").read_text()
    assert "memory_remember" in text


def test_cli_uninstall_round_trip(tmp_path: Path, capsys):
    (tmp_path / "CLAUDE.md").write_text("# X\n")
    cli_main(["install-claude-md", "--path", str(tmp_path)])
    capsys.readouterr()
    code = cli_main(["uninstall-claude-md", "--path", str(tmp_path)])
    assert code == 0
    text = (tmp_path / "CLAUDE.md").read_text()
    assert not has_protocol(text)


def test_cli_install_with_explicit_target_outside_root(tmp_path: Path):
    nested = tmp_path / ".claude"
    nested.mkdir()
    target = nested / "CLAUDE.md"
    target.write_text("# nested\n")
    code = cli_main([
        "install-claude-md",
        "--path", str(tmp_path),
        "--target", str(target),
    ])
    assert code == 0
    assert has_protocol(target.read_text())


def test_cli_install_picks_dotclaude_fallback(tmp_path: Path):
    """If only .claude/CLAUDE.md exists, use it."""
    (tmp_path / ".claude").mkdir()
    target = tmp_path / ".claude" / "CLAUDE.md"
    target.write_text("# nested\n")
    code = cli_main(["install-claude-md", "--path", str(tmp_path)])
    assert code == 0
    assert has_protocol(target.read_text())
    # Did NOT create a root-level CLAUDE.md.
    assert not (tmp_path / "CLAUDE.md").exists()


def test_help_lists_new_commands(capsys):
    with pytest.raises(SystemExit) as exc:
        cli_main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "install-claude-md" in out
    assert "uninstall-claude-md" in out
