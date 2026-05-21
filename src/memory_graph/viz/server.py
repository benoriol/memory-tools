"""Read-only HTTP server that exposes a memory store as JSON + a viewer.

  GET /                    -> the viewer HTML (vis-network from CDN)
  GET /api/graph           -> {nodes, edges, stats}
  GET /api/note/<id>       -> full note (body, edges, tags, anchors)
  GET /api/operator        -> current operator-context markdown

The store is opened read-only — no embeddings are computed; we read
straight from SQLite. The Store class isn't used because we don't need
its mutation methods or embedder.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any

from memory_graph.storage.files import NOTES_DIRNAME


def _open_index(store_root: Path) -> sqlite3.Connection:
    db = store_root / "index.db"
    if not db.exists():
        raise FileNotFoundError(f"no index.db at {db} — run `memory-graph init`")
    # Read-only via the SQLite URI scheme so accidental writes can't slip through.
    uri = f"file:{db}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _graph_json(conn: sqlite3.Connection) -> dict[str, Any]:
    """Build the JSON payload for the viewer."""
    nodes: list[dict[str, Any]] = []
    for r in conn.execute(
        "SELECT id, title, short_label, summary, kind, status, created_at,"
        " updated_at, happened_at, last_verified_at, confidence FROM nodes"
    ):
        nodes.append(
            {
                "id": r["id"],
                "title": r["title"],
                "short_label": r["short_label"],
                "summary": r["summary"],
                "kind": r["kind"],
                "status": r["status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "happened_at": r["happened_at"],
                "last_verified_at": r["last_verified_at"],
                "confidence": r["confidence"],
            }
        )
    edges: list[dict[str, Any]] = []
    for r in conn.execute("SELECT from_id, to_id, type, weight FROM edges"):
        edges.append(
            {
                "from": r["from_id"],
                "to": r["to_id"],
                "type": r["type"],
                "weight": r["weight"],
            }
        )
    by_kind: dict[str, int] = {}
    for r in conn.execute("SELECT kind, COUNT(*) AS n FROM nodes GROUP BY kind"):
        by_kind[r["kind"]] = r["n"]
    by_edge: dict[str, int] = {}
    for r in conn.execute("SELECT type, COUNT(*) AS n FROM edges GROUP BY type"):
        by_edge[r["type"]] = r["n"]
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "by_kind": by_kind,
            "by_edge_type": by_edge,
        },
    }


def _note_json(conn: sqlite3.Connection, store_root: Path, note_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, title, short_label, summary, body, kind, status, created_at,"
        " updated_at, happened_at, last_verified_at, confidence, cluster_id,"
        " source_path FROM nodes WHERE id = ?",
        (note_id,),
    ).fetchone()
    if row is None:
        return None
    # Prefer reading the canonical body off disk when possible — the markdown
    # file is the source of truth.
    md = store_root / NOTES_DIRNAME / f"{note_id}.md"
    body = row["body"]
    if md.exists():
        try:
            body = md.read_text(encoding="utf-8")
        except OSError:
            pass
    edges = [
        {"to": r["to_id"], "type": r["type"], "weight": r["weight"]}
        for r in conn.execute(
            "SELECT to_id, type, weight FROM edges WHERE from_id = ?", (note_id,)
        )
    ]
    incoming = [
        {"from": r["from_id"], "type": r["type"], "weight": r["weight"]}
        for r in conn.execute(
            "SELECT from_id, type, weight FROM edges WHERE to_id = ?", (note_id,)
        )
    ]
    tags = [
        r["tag"]
        for r in conn.execute(
            "SELECT tag FROM tags WHERE node_id = ? ORDER BY tag", (note_id,)
        )
    ]
    anchors = [
        {"path": r["path"], "pattern": r["pattern"], "commit": r["commit_sha"]}
        for r in conn.execute(
            "SELECT path, pattern, commit_sha FROM anchors WHERE node_id = ?",
            (note_id,),
        )
    ]
    return {
        "id": row["id"],
        "title": row["title"],
        "short_label": row["short_label"],
        "summary": row["summary"],
        "body_markdown": body,
        "kind": row["kind"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "happened_at": row["happened_at"],
        "last_verified_at": row["last_verified_at"],
        "confidence": row["confidence"],
        "cluster_id": row["cluster_id"],
        "tags": tags,
        "edges": edges,
        "incoming": incoming,
        "anchors": anchors,
    }


def _operator_text(store_root: Path) -> str:
    p = store_root / "_operator" / "context.md"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def _index_html() -> bytes:
    return files("memory_graph.viz").joinpath("static/index.html").read_bytes()


def _make_handler(store_root: Path) -> type[BaseHTTPRequestHandler]:
    """Build a request handler with the store_root bound in closure."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:  # quieter logs
            # Keep errors visible; drop the per-request access lines.
            if "404" in (fmt % args) or "500" in (fmt % args):
                super().log_message(fmt, *args)

        def _send_json(self, payload: Any, status: int = 200) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _send_html(self, data: bytes) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_error(self, status: int, msg: str) -> None:
            self._send_json({"error": msg}, status=status)

        def do_GET(self) -> None:  # noqa: N802 — stdlib name
            path = self.path.split("?", 1)[0]
            try:
                if path in ("/", "/index.html"):
                    self._send_html(_index_html())
                    return
                if path == "/api/graph":
                    conn = _open_index(store_root)
                    try:
                        self._send_json(_graph_json(conn))
                    finally:
                        conn.close()
                    return
                if path == "/api/operator":
                    self._send_json({"markdown": _operator_text(store_root)})
                    return
                if path.startswith("/api/note/"):
                    note_id = path[len("/api/note/") :]
                    conn = _open_index(store_root)
                    try:
                        note = _note_json(conn, store_root, note_id)
                    finally:
                        conn.close()
                    if note is None:
                        self._send_error(404, f"no note with id {note_id!r}")
                        return
                    self._send_json(note)
                    return
                self._send_error(404, f"unknown path: {path}")
            except Exception as exc:  # pragma: no cover
                self._send_error(500, f"{type(exc).__name__}: {exc}")

    return Handler


def serve(
    store_root: str | Path,
    *,
    port: int = 8765,
    host: str = "127.0.0.1",
    open_browser: bool = True,
) -> None:
    """Run the viewer server until Ctrl+C."""
    root = Path(store_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(
            f"no .memory-graph/ at {root}. Run `memory-graph init` in the "
            "project, or pass --path pointing at the .memory-graph/ dir."
        )

    # Open the SQLite index once in write mode. This:
    #   (1) creates index.db on a freshly-init'd store that's never been
    #       written to (the dir exists, the .db doesn't yet);
    #   (2) applies any additive schema changes (new nullable columns)
    #       before the read-only request handlers start querying — they
    #       open `mode=ro` per request which can't ALTER.
    from memory_graph.storage.db import open_db as _open_db_rw
    _open_db_rw(root / "index.db").close()

    handler = _make_handler(root)
    httpd = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(f"memory-graph viz serving {root} at {url}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping.")
    finally:
        httpd.server_close()
