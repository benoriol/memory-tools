"""On-disk layout helpers for the `.memory-recall/` store."""

from __future__ import annotations

from pathlib import Path

from memory_recall.storage import STORE_DIRNAME

_DEFAULT_CONFIG = """\
# memory-recall store config
embedding_model: sentence-transformers/all-MiniLM-L6-v2
embedding_dim: 384
"""

_GITIGNORE = "store.db\nstore.db-journal\n"


def store_root(start: Path | None = None) -> Path:
    """Walk upward from `start` (default cwd) until a `.memory-recall/` dir is found."""
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        target = candidate / STORE_DIRNAME
        if target.is_dir():
            return target
    raise FileNotFoundError(
        f"No {STORE_DIRNAME}/ found in {here} or any parent. Run `memory-recall init`."
    )


def init_store(path: Path) -> Path:
    """Create `.memory-recall/{config.yml, .gitignore, notes/}` under `path`."""
    root = path / STORE_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    (root / "notes").mkdir(exist_ok=True)
    config = root / "config.yml"
    if not config.exists():
        config.write_text(_DEFAULT_CONFIG)
    gi = root / ".gitignore"
    if not gi.exists():
        gi.write_text(_GITIGNORE)
    return root


def notes_dir(root: Path) -> Path:
    return root / "notes"


def note_md_path(root: Path, note_id: str) -> Path:
    return notes_dir(root) / f"{note_id}.md"
