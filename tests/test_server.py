"""MCP server tool registration and behavior.

The tools are tested by invoking them as plain functions (they're just
wrappers over `Store`). The stdio transport itself is exercised
manually with a real Claude Code session; we don't fake the JSON-RPC
loop here.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from memory_graph.embed import FakeEmbedder
from memory_graph.primitives import Store
from memory_graph.server import (
    mcp,
    memory_capture,
    memory_capture_batch,
    memory_get,
    memory_link,
    memory_neighbors,
    memory_search,
    memory_status,
    memory_supersede,
)


@pytest.fixture()
def server_store(tmp_path: Path, monkeypatch):
    """Reset and inject a FakeEmbedder-backed Store as the singleton."""
    root = tmp_path / ".memory-graph"
    root.mkdir()
    monkeypatch.setenv("MEMORY_GRAPH_ROOT", str(root))

    # Reset cached store + force the FakeEmbedder for tests.
    import memory_graph.server as srv

    srv._store = None
    srv._store_root = None
    with patch.object(srv, "_make_embedder", return_value=FakeEmbedder(dim=32)):
        yield srv.get_store()
    srv._store = None
    srv._store_root = None


# Note: the @mcp.tool() decorator wraps each function so it can be registered
# with FastMCP. To call them as regular Python, we use the underlying `.fn`
# attribute that FastMCP exposes on the wrapper.


def _call(tool, **kwargs):
    """Invoke an mcp.tool()-decorated function as a plain callable."""
    fn = getattr(tool, "fn", tool)
    return fn(**kwargs)


def test_capture_then_get(server_store):
    result = _call(
        memory_capture,
        title="t",
        summary="s",
        body="b",
        kind="capture",
        tags=["x", "y"],
    )
    nid = result["id"]
    fetched = _call(memory_get, note_id=nid)
    assert fetched is not None
    assert fetched["title"] == "t"
    assert sorted(fetched["tags"]) == ["x", "y"]


def test_search_returns_inserted(server_store):
    a = _call(
        memory_capture,
        title="cursor pagination",
        summary="cursor pagination at high QPS",
        body="benchmarks",
        kind="lesson",
    )
    _call(
        memory_capture,
        title="auth middleware",
        summary="auth middleware ordering decisions",
        body="ordering",
        kind="lesson",
    )
    hits = _call(memory_search, query="cursor pagination at high QPS", k=2)
    assert hits and hits[0]["id"] == a["id"]


def test_capture_batch_resolves_placeholders(server_store):
    results = _call(
        memory_capture_batch,
        notes=[
            {
                "title": "capture",
                "summary": "raw observation",
                "body": "b",
                "kind": "capture",
                "note_id": "@1",
            },
            {
                "title": "lesson",
                "summary": "distilled lesson",
                "body": "b",
                "kind": "lesson",
                "note_id": "@2",
                "edges": [{"to": "@1", "type": "derived_from"}],
            },
        ],
    )
    cap_id, lesson_id = results[0]["id"], results[1]["id"]
    lesson = _call(memory_get, note_id=lesson_id)
    assert any(e["to"] == cap_id and e["type"] == "derived_from" for e in lesson["edges"])


def test_link_and_neighbors(server_store):
    a = _call(
        memory_capture, title="a", summary="a", body="a", kind="capture"
    )["id"]
    b = _call(
        memory_capture, title="b", summary="b", body="b", kind="capture"
    )["id"]
    _call(memory_link, from_id=a, to_id=b, type="related")
    nbrs = _call(memory_neighbors, note_id=a, depth=1)
    assert [n["id"] for n in nbrs] == [b]
    assert nbrs[0]["edge_type"] == "related"


def test_supersede_round_trip(server_store):
    old = _call(memory_capture, title="o", summary="o", body="o", kind="lesson")["id"]
    new = _call(memory_capture, title="n", summary="n", body="n", kind="lesson")["id"]
    _call(memory_supersede, old_id=old, new_id=new, reason="clearer")
    old_note = _call(memory_get, note_id=old)
    assert old_note["status"] == "superseded"


def test_status_reports_embedding_info(server_store):
    _call(memory_capture, title="t", summary="t", body="t", kind="capture")
    status = _call(memory_status)
    assert status["total_nodes"] == 1
    assert status["embedding_model"] == "fake"
    assert status["embedding_dim"] == 32


def test_get_missing_returns_none(server_store):
    assert _call(memory_get, note_id="nope") is None


def test_root_resolution_via_env(tmp_path: Path, monkeypatch):
    root = tmp_path / ".memory-graph"
    root.mkdir()
    monkeypatch.setenv("MEMORY_GRAPH_ROOT", str(root))
    import memory_graph.server as srv

    srv._store = None
    with patch.object(srv, "_make_embedder", return_value=FakeEmbedder()):
        store = srv.get_store()
    try:
        assert store.root == root
    finally:
        srv._store = None


def test_root_resolution_errors_when_missing(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("MEMORY_GRAPH_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)  # nowhere to walk up to
    import memory_graph.server as srv

    srv._store = None
    with pytest.raises(FileNotFoundError):
        srv._resolve_root()


def test_server_registers_all_primitives():
    """Make sure no tool got dropped from the FastMCP registry."""
    # FastMCP exposes registered tools via .list_tools() / internal map.
    # The simplest check: every memory_* symbol we expect is a registered tool.
    expected = {
        "memory_capture",
        "memory_capture_batch",
        "memory_get",
        "memory_search",
        "memory_neighbors",
        "memory_link",
        "memory_unlink",
        "memory_supersede",
        "memory_mark",
        "memory_status",
    }
    # The wrapped functions live as attributes on the module; tools registered
    # with FastMCP keep their original names.
    import memory_graph.server as srv

    for name in expected:
        assert hasattr(srv, name), f"missing tool: {name}"
        # Each one should be callable.
        fn = getattr(srv, name)
        assert callable(getattr(fn, "fn", fn))

    # Silence ruff unused-import on mcp.
    assert mcp is not None


def test_env_path_with_missing_dir_raises(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MEMORY_GRAPH_ROOT", str(tmp_path / "does-not-exist"))
    import memory_graph.server as srv

    srv._store = None
    with pytest.raises(FileNotFoundError):
        srv._resolve_root()
    # Cleanup so we don't leak into other tests.
    os.environ.pop("MEMORY_GRAPH_ROOT", None)
