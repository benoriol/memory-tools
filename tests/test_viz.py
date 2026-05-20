"""HTTP viewer: API endpoints + HTML serving."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from memory_graph.embed import FakeEmbedder
from memory_graph.primitives import Store
from memory_graph.storage import Edge
from memory_graph.viz.server import (
    _graph_json,
    _make_handler,
    _note_json,
    _open_index,
)


@pytest.fixture()
def populated_store(store: Path):
    """Returns (store_root, {"alpha": id, "beta": id, "gamma": id})."""
    with Store(store, embedder=FakeEmbedder(dim=32)) as s:
        a = s.capture(title="alpha", summary="alpha sum", body="alpha body", kind="lesson")
        b = s.capture(
            title="beta", summary="beta sum", body="beta body", kind="capture",
            tags=["one", "two"],
        )
        c = s.capture(
            title="gamma", summary="gamma sum", body="gamma body", kind="principle",
            edges=[Edge(to_id=a["id"], type="generalizes")],
        )
        s.link(b["id"], a["id"], "derived_from")
    return store, {"alpha": a["id"], "beta": b["id"], "gamma": c["id"]}


# -- direct helper functions ------------------------------------------------


def test_graph_json_counts_and_shapes(populated_store):
    root, _ = populated_store
    conn = _open_index(root)
    try:
        g = _graph_json(conn)
    finally:
        conn.close()
    assert g["stats"]["total_nodes"] == 3
    assert g["stats"]["total_edges"] == 2
    assert set(g["stats"]["by_kind"]) == {"lesson", "capture", "principle"}
    # Every node has the fields the viewer reads.
    for n in g["nodes"]:
        for key in ("id", "title", "summary", "kind", "status"):
            assert key in n
    for e in g["edges"]:
        for key in ("from", "to", "type", "weight"):
            assert key in e


def test_note_json_includes_body_edges_tags_incoming(populated_store):
    root, ids = populated_store
    conn = _open_index(root)
    try:
        # beta points to alpha via derived_from, and has tags
        note = _note_json(conn, root, ids["beta"])
    finally:
        conn.close()
    assert note is not None
    assert note["title"] == "beta"
    assert sorted(note["tags"]) == ["one", "two"]
    out_types = {e["type"] for e in note["edges"]}
    assert "derived_from" in out_types
    # alpha should be reachable via beta → alpha
    targets = {e["to"] for e in note["edges"]}
    assert ids["alpha"] in targets


def test_note_json_returns_none_for_missing(populated_store):
    root, _ = populated_store
    conn = _open_index(root)
    try:
        assert _note_json(conn, root, "no-such-id") is None
    finally:
        conn.close()


def test_open_index_errors_when_db_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        _open_index(tmp_path)


# -- end-to-end over HTTP ---------------------------------------------------


def _serve_in_thread(handler_cls):
    """Start a one-shot ThreadingHTTPServer on a random port."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    # Give the server a tick to start accepting connections.
    time.sleep(0.05)
    return httpd, port


def _get(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=2.0) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def test_http_root_serves_html(populated_store):
    root, _ = populated_store
    httpd, port = _serve_in_thread(_make_handler(root))
    try:
        status, body = _get(f"http://127.0.0.1:{port}/")
        assert status == 200
        text = body.decode("utf-8")
        assert "<title>memory-graph viewer</title>" in text
        # vis-network from the CDN — confirms we serve the real template.
        assert "vis-network" in text
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_http_graph_endpoint(populated_store):
    root, ids = populated_store
    httpd, port = _serve_in_thread(_make_handler(root))
    try:
        status, body = _get(f"http://127.0.0.1:{port}/api/graph")
        assert status == 200
        data = json.loads(body)
        assert data["stats"]["total_nodes"] == 3
        node_ids = {n["id"] for n in data["nodes"]}
        assert ids["alpha"] in node_ids
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_http_note_endpoint_and_404(populated_store):
    root, ids = populated_store
    httpd, port = _serve_in_thread(_make_handler(root))
    try:
        # Happy path.
        status, body = _get(f"http://127.0.0.1:{port}/api/note/{ids['gamma']}")
        assert status == 200
        data = json.loads(body)
        assert data["title"] == "gamma"

        # 404.
        status, body = _get(f"http://127.0.0.1:{port}/api/note/no-such-id")
        assert status == 404
        data = json.loads(body)
        assert "error" in data
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_http_operator_endpoint(populated_store):
    root, _ = populated_store
    # Seed an operator context file.
    op = root / "_operator" / "context.md"
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text("custom operator notes\n")

    httpd, port = _serve_in_thread(_make_handler(root))
    try:
        status, body = _get(f"http://127.0.0.1:{port}/api/operator")
        assert status == 200
        data = json.loads(body)
        assert data["markdown"].strip() == "custom operator notes"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_http_unknown_path_404(populated_store):
    root, _ = populated_store
    httpd, port = _serve_in_thread(_make_handler(root))
    try:
        status, _ = _get(f"http://127.0.0.1:{port}/api/does-not-exist")
        assert status == 404
    finally:
        httpd.shutdown()
        httpd.server_close()
