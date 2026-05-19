"""Markdown-with-frontmatter I/O for notes.

The markdown file is the source of truth; the SQLite index is derived.
Frontmatter is YAML between two `---` lines at the top of the file.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from memory_graph.storage.note import Anchor, Edge, Note

STORE_DIRNAME = ".memory-graph"
NOTES_DIRNAME = "notes"

_FRONTMATTER_DELIM = "---"


def store_root(start: str | Path | None = None) -> Path:
    """Find the `.memory-graph` directory by walking up from `start` (or CWD)."""
    here = Path(start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        target = candidate / STORE_DIRNAME
        if target.is_dir():
            return target
    raise FileNotFoundError(
        f"No {STORE_DIRNAME}/ found at or above {here}. "
        "Run `memory-graph init` in the project root first."
    )


def note_path(store: Path, note_id: str) -> Path:
    """Filesystem path for the markdown file backing a note id."""
    return store / NOTES_DIRNAME / f"{note_id}.md"


def write_note(store: Path, note: Note) -> Path:
    """Persist `note` to its markdown file under `store`. Returns the path."""
    notes_dir = store / NOTES_DIRNAME
    notes_dir.mkdir(parents=True, exist_ok=True)
    path = note_path(store, note.id)
    path.write_text(_render(note), encoding="utf-8")
    return path


def read_note(path: str | Path) -> Note:
    """Parse a note from disk. Raises if frontmatter is missing or malformed."""
    text = Path(path).read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)
    data = yaml.safe_load(frontmatter) or {}
    return _from_frontmatter(data, body, source_path=str(Path(path).resolve()))


def _render(note: Note) -> str:
    fm: dict = {
        "id": note.id,
        "title": note.title,
        "summary": note.summary,
        "kind": note.kind,
        "status": note.status,
        "created_at": note.created_at,
        "updated_at": note.updated_at,
        "confidence": note.confidence,
    }
    if note.happened_at is not None:
        fm["happened_at"] = note.happened_at
    if note.last_verified_at is not None:
        fm["last_verified_at"] = note.last_verified_at
    if note.tags:
        fm["tags"] = list(note.tags)
    if note.edges:
        fm["edges"] = [
            {"to": e.to_id, "type": e.type, **({"weight": e.weight} if e.weight != 1.0 else {})}
            for e in note.edges
        ]
    if note.anchors:
        fm["anchors"] = [
            {
                "path": a.path,
                **({"pattern": a.pattern} if a.pattern else {}),
                **({"commit": a.commit_sha} if a.commit_sha else {}),
            }
            for a in note.anchors
        ]
    if note.cluster_id is not None:
        fm["cluster_id"] = note.cluster_id

    yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    return f"{_FRONTMATTER_DELIM}\n{yaml_text}\n{_FRONTMATTER_DELIM}\n\n{note.body.rstrip()}\n"


def _split_frontmatter(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        raise ValueError("Note is missing leading '---' frontmatter delimiter")
    for i in range(1, len(lines)):
        if lines[i].strip() == _FRONTMATTER_DELIM:
            frontmatter = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1 :]).lstrip("\n")
            return frontmatter, body
    raise ValueError("Note has no closing '---' frontmatter delimiter")


def _from_frontmatter(data: dict, body: str, source_path: str) -> Note:
    edges = [
        Edge(to_id=e["to"], type=e["type"], weight=float(e.get("weight", 1.0)))
        for e in data.get("edges", []) or []
    ]
    anchors = [
        Anchor(
            path=a["path"],
            pattern=a.get("pattern", ""),
            commit_sha=a.get("commit"),
        )
        for a in data.get("anchors", []) or []
    ]
    return Note(
        id=data["id"],
        title=data["title"],
        summary=data["summary"],
        body=body,
        kind=data["kind"],
        status=data.get("status", "active"),
        created_at=int(data.get("created_at", 0)),
        updated_at=int(data.get("updated_at", 0)),
        happened_at=_optional_int(data.get("happened_at")),
        last_verified_at=_optional_int(data.get("last_verified_at")),
        confidence=float(data.get("confidence", 1.0)),
        tags=list(data.get("tags", []) or []),
        edges=edges,
        anchors=anchors,
        cluster_id=_optional_int(data.get("cluster_id")),
        body_hash=data.get("body_hash"),
        source_path=source_path,
    )


def _optional_int(value) -> int | None:
    return None if value is None else int(value)
