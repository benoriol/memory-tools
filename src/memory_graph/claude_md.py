"""Install / update / detect the memory protocol section in a CLAUDE.md.

The section is wrapped in HTML-comment sentinels:

    <!-- memory-graph-mcp:protocol:start -->
    ... content ...
    <!-- memory-graph-mcp:protocol:end -->

so we can find it back later, replace it cleanly with --force, or
detect that the user's already installed it.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

START_MARKER = "<!-- memory-graph-mcp:protocol:start"
END_MARKER = "<!-- memory-graph-mcp:protocol:end -->"

# Names we'll look at, in priority order, when no explicit --target is given.
DEFAULT_CANDIDATE_FILENAMES = ("CLAUDE.md", ".claude/CLAUDE.md")


def template_text() -> str:
    """Return the bundled CLAUDE.md memory-protocol template."""
    return files("memory_graph.templates").joinpath("claude_protocol.md").read_text(
        encoding="utf-8"
    )


def find_target(project_root: Path) -> Path | None:
    """Return the first CLAUDE.md-like file we find in `project_root`, or None."""
    for rel in DEFAULT_CANDIDATE_FILENAMES:
        candidate = project_root / rel
        if candidate.is_file():
            return candidate
    return None


def has_protocol(text: str) -> bool:
    """True if `text` already contains the start sentinel."""
    return START_MARKER in text


def extract_protocol_block(text: str) -> tuple[int, int] | None:
    """Return (start_idx, end_idx_exclusive) of the protocol block, or None.

    `start_idx` is the first character of the start-marker line.
    `end_idx_exclusive` is one past the newline that follows the end marker.
    """
    s = text.find(START_MARKER)
    if s < 0:
        return None
    e = text.find(END_MARKER, s)
    if e < 0:
        return None
    # Walk to the end of the end-marker line (consume the trailing newline).
    line_end = text.find("\n", e)
    end_exclusive = (line_end + 1) if line_end != -1 else len(text)
    # Walk back to include the start of the start-marker line.
    line_start = text.rfind("\n", 0, s) + 1  # 0 if no preceding newline
    return line_start, end_exclusive


def install(
    target: Path,
    *,
    force: bool = False,
    template: str | None = None,
) -> tuple[str, str]:
    """Ensure the memory protocol is present in `target`.

    Returns (status, message) where status is one of:
      "installed"   — appended a fresh section
      "unchanged"   — protocol already present and matches the template
      "stale"       — protocol present but differs from the template;
                      pass force=True to replace
      "replaced"    — protocol present and replaced (force=True)
    """
    content = target.read_text(encoding="utf-8") if target.exists() else ""
    new_block = template if template is not None else template_text()
    if not new_block.endswith("\n"):
        new_block += "\n"

    existing = extract_protocol_block(content)
    if existing is None:
        # Append. Ensure exactly one blank line of separation from prior content.
        if content and not content.endswith("\n"):
            content += "\n"
        if content and not content.endswith("\n\n"):
            content += "\n"
        target.write_text(content + new_block, encoding="utf-8")
        return "installed", f"appended memory protocol to {target}"

    s, e = existing
    current_block = content[s:e]
    if current_block.strip() == new_block.strip():
        return "unchanged", f"memory protocol already current in {target}"
    if not force:
        return (
            "stale",
            f"memory protocol already present in {target} but differs from the "
            "bundled template. Pass --force to replace, or edit by hand.",
        )
    target.write_text(content[:s] + new_block + content[e:], encoding="utf-8")
    return "replaced", f"replaced memory protocol in {target}"


def uninstall(target: Path) -> tuple[str, str]:
    """Remove the protocol block from `target` if present."""
    if not target.exists():
        return "missing", f"{target} does not exist"
    content = target.read_text(encoding="utf-8")
    existing = extract_protocol_block(content)
    if existing is None:
        return "absent", f"no memory protocol section in {target}"
    s, e = existing
    new = content[:s] + content[e:]
    # Tidy up: collapse runs of 3+ newlines down to 2.
    while "\n\n\n" in new:
        new = new.replace("\n\n\n", "\n\n")
    target.write_text(new, encoding="utf-8")
    return "removed", f"removed memory protocol from {target}"
