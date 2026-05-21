"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory_recall.storage import STORE_DIRNAME


@pytest.fixture()
def store_root(tmp_path: Path) -> Path:
    """A fresh `.memory-recall/` directory inside a tmp_path."""
    root = tmp_path / STORE_DIRNAME
    root.mkdir()
    (root / "notes").mkdir()
    return root
