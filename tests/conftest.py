"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory_graph.storage import STORE_DIRNAME


@pytest.fixture()
def store(tmp_path: Path) -> Path:
    """A fresh `.memory-graph/` directory inside a tmp_path."""
    root = tmp_path / STORE_DIRNAME
    root.mkdir()
    return root
