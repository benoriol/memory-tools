"""`memory-graph` CLI.

Subcommands:
  init       Create .memory-graph/ in the current project.
  serve      Run the MCP server on stdio (used by Claude Code).
  digest     End-of-session reflection (Stop-hook entry point).
  reindex    Rebuild the SQLite index from markdown notes.
  status     Print store stats as JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from memory_graph.storage.files import NOTES_DIRNAME, STORE_DIRNAME

CONFIG_FILE = "config.yml"
DEFAULT_CONFIG = """\
# memory-graph store config

embedding:
  model: sentence-transformers/all-MiniLM-L6-v2
  provider: fastembed
"""


# ----------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    """Create .memory-graph/ in `--path` (default: cwd)."""
    project = Path(args.path).resolve()
    root = project / STORE_DIRNAME
    if root.exists():
        print(f"Already initialized: {root}", file=sys.stderr)
        return 1
    (root / NOTES_DIRNAME).mkdir(parents=True)
    (root / "_operator").mkdir()
    (root / "_pending").mkdir()
    (root / CONFIG_FILE).write_text(DEFAULT_CONFIG)
    # A gentle gitignore inside the store so users can commit notes but
    # keep machine-local SQLite/cache out of the repo.
    (root / ".gitignore").write_text("index.db\nindex.db-*\n.cache/\n")
    print(f"Initialized {root}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Run the MCP server on stdio."""
    from memory_graph.server import main as serve_main

    serve_main()
    return 0


def cmd_digest(args: argparse.Namespace) -> int:
    """End-of-session digest.

    Reads the transcript pointed to by `--transcript` (or
    $CLAUDE_TRANSCRIPT_PATH) and hands it to the memory sub-agent's
    remember flow. This is the Stop-hook entry point.
    """
    path = args.transcript or os.environ.get("CLAUDE_TRANSCRIPT_PATH")
    if not path:
        print(
            "no transcript provided (pass --transcript or set "
            "$CLAUDE_TRANSCRIPT_PATH)",
            file=sys.stderr,
        )
        return 2
    transcript = Path(path).read_text(encoding="utf-8")
    if not transcript.strip():
        print("transcript is empty; nothing to digest", file=sys.stderr)
        return 0

    store = _open_store_or_die()
    try:
        from memory_graph.orchestration import remember_sync
    except ImportError:
        print(
            "claude-agent-sdk is not installed; install with "
            "`pip install memory-graph-mcp[agent]`",
            file=sys.stderr,
        )
        return 3
    synthesis = remember_sync(transcript, store=store)
    print(synthesis)
    return 0


def cmd_reindex(args: argparse.Namespace) -> int:
    """Rebuild the SQLite index from the markdown files.

    Used after manual edits, a `git pull` that changed `notes/`, or a
    schema bump.

    Three passes so foreign-key constraints don't bite when an edge
    references a node that sorts later than its source:
      1. Insert every node (without its outgoing edges) plus its tags
         and anchors.
      2. Insert every edge.
      3. Re-embed each note (skipped with --no-embed).
    """
    from memory_graph.embed import LocalEmbedder
    from memory_graph.embed.base import build_embed_input
    from memory_graph.primitives import Store
    from memory_graph.storage import read_note

    root = _resolve_root_path(args.path)
    db_path = root / "index.db"
    if db_path.exists() and not args.keep_db:
        db_path.unlink()
    notes_dir = root / NOTES_DIRNAME
    if not notes_dir.is_dir():
        print(f"no notes directory at {notes_dir}", file=sys.stderr)
        return 1

    embedder = LocalEmbedder() if not args.no_embed else _NullEmbedder()
    notes = [read_note(md) for md in sorted(notes_dir.glob("*.md"))]

    with Store(root, embedder=embedder) as s:
        # Pass 1: nodes (and tags + anchors), no edges yet.
        for note in notes:
            saved_edges = list(note.edges)
            note.edges = []
            try:
                s._insert_node(note)
            finally:
                note.edges = saved_edges

        # Pass 2: edges. All target nodes now exist.
        for note in notes:
            for e in note.edges:
                s.link(note.id, e.to_id, e.type, weight=e.weight)

        # Pass 3: embeddings.
        if not args.no_embed:
            for note in notes:
                text = build_embed_input(note.title, note.summary, note.body)
                vec = embedder.embed(text)
                s._upsert_embedding(note.id, note.body_hash or "", vec)

    print(f"rebuilt {len(notes)} notes into {db_path}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Print the store's stats as JSON."""
    from memory_graph.embed import LocalEmbedder
    from memory_graph.primitives import Store

    root = _resolve_root_path(args.path)
    with Store(root, embedder=LocalEmbedder()) as s:
        print(json.dumps(s.status(), indent=2))
    return 0


def cmd_register(args: argparse.Namespace) -> int:
    """Write/merge the MCP server config for this tool.

    `--scope project` (default): writes ./.mcp.json in the current dir so
    only this project's Claude Code sessions see the server.

    `--scope user`: merges into ~/.claude.json so every project does.

    The OAuth token is taken from `--token` if given, otherwise from
    $CLAUDE_CODE_OAUTH_TOKEN. If neither is set, we still write the
    config (with an empty token value) and print a warning so you can
    fill it in by hand.
    """
    binary = _resolve_binary_path(args.binary)
    if binary is None:
        print(
            "could not locate the `memory-graph` binary on PATH. "
            "Pass --binary /abs/path/to/memory-graph explicitly.",
            file=sys.stderr,
        )
        return 1

    token = args.token or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")

    entry = {
        "command": binary,
        "args": ["serve"],
        "env": {"CLAUDE_CODE_OAUTH_TOKEN": token},
    }

    if args.scope == "user":
        target = Path.home() / ".claude.json"
    else:
        target = Path(args.path).resolve() / ".mcp.json"

    data = _read_json(target)
    servers = data.setdefault("mcpServers", {})
    if args.name in servers and not args.force:
        print(
            f"`{args.name}` already registered in {target}. "
            "Use --force to overwrite.",
            file=sys.stderr,
        )
        return 1
    servers[args.name] = entry
    target.write_text(json.dumps(data, indent=2) + "\n")

    print(f"Registered `{args.name}` in {target}")
    if not token:
        print(
            "  warning: CLAUDE_CODE_OAUTH_TOKEN is empty. Run "
            "`claude setup-token` to get one, then edit the file or "
            "re-run with --token.",
            file=sys.stderr,
        )
    return 0


def cmd_viz(args: argparse.Namespace) -> int:
    """Serve a local web viewer for the project's memory graph."""
    from memory_graph.viz import serve

    root = _resolve_root_path(args.path)
    serve(
        root,
        port=args.port,
        host=args.host,
        open_browser=not args.no_browser,
    )
    return 0


def cmd_unregister(args: argparse.Namespace) -> int:
    """Remove this tool's entry from .mcp.json or ~/.claude.json."""
    if args.scope == "user":
        target = Path.home() / ".claude.json"
    else:
        target = Path(args.path).resolve() / ".mcp.json"

    if not target.exists():
        print(f"nothing to do: {target} does not exist", file=sys.stderr)
        return 0

    data = _read_json(target)
    servers = data.get("mcpServers", {})
    if args.name not in servers:
        print(f"`{args.name}` not present in {target}", file=sys.stderr)
        return 0
    del servers[args.name]
    target.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Removed `{args.name}` from {target}")
    return 0


# ----------------------------------------------------------------------------


def _resolve_root_path(start: str | None) -> Path:
    """Walk up from `start` (or CWD) looking for .memory-graph/."""
    from memory_graph.storage.files import store_root

    return store_root(start) if start else store_root()


def _resolve_binary_path(explicit: str | None) -> str | None:
    """Find the absolute path to the `memory-graph` console entry."""
    if explicit:
        return str(Path(explicit).resolve())
    found = shutil.which("memory-graph")
    if found:
        return str(Path(found).resolve())
    # Fall back: try the entry inside the same venv as the current Python.
    candidate = Path(sys.executable).parent / "memory-graph"
    if candidate.exists():
        return str(candidate.resolve())
    return None


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text() or "{}"
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"refusing to overwrite malformed JSON at {path}: {exc}")


def _open_store_or_die():
    from memory_graph.embed import LocalEmbedder
    from memory_graph.primitives import Store

    root = _resolve_root_path(None)
    return Store(root, embedder=LocalEmbedder())


class _NullEmbedder:
    """Used when --no-embed is passed to reindex (fast rebuild for inspection)."""

    name = "null"
    dim = 0

    def embed(self, text: str):  # pragma: no cover
        raise RuntimeError("null embedder cannot embed")

    def embed_batch(self, texts):  # pragma: no cover
        raise RuntimeError("null embedder cannot embed")


# ----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="memory-graph")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="initialize a project store")
    p_init.add_argument(
        "--path", default=".", help="project root (default: cwd)"
    )
    p_init.set_defaults(func=cmd_init)

    p_serve = sub.add_parser("serve", help="run the MCP server on stdio")
    p_serve.set_defaults(func=cmd_serve)

    p_digest = sub.add_parser("digest", help="end-of-session digest (Stop hook)")
    p_digest.add_argument(
        "--transcript",
        help="path to the Claude Code transcript (or set $CLAUDE_TRANSCRIPT_PATH)",
    )
    p_digest.set_defaults(func=cmd_digest)

    p_reindex = sub.add_parser(
        "reindex", help="rebuild the SQLite index from markdown notes"
    )
    p_reindex.add_argument("--path", default=None)
    p_reindex.add_argument(
        "--no-embed",
        action="store_true",
        help="rebuild the index without recomputing embeddings",
    )
    p_reindex.add_argument(
        "--keep-db",
        action="store_true",
        help="don't delete the existing DB before reindexing",
    )
    p_reindex.set_defaults(func=cmd_reindex)

    p_status = sub.add_parser("status", help="print store stats as JSON")
    p_status.add_argument("--path", default=None)
    p_status.set_defaults(func=cmd_status)

    p_register = sub.add_parser(
        "register",
        help="write/merge the MCP server entry into .mcp.json or ~/.claude.json",
    )
    p_register.add_argument(
        "--scope",
        choices=["project", "user"],
        default="project",
        help="project (./.mcp.json, default) or user (~/.claude.json)",
    )
    p_register.add_argument("--path", default=".", help="project root for --scope=project")
    p_register.add_argument(
        "--name", default="memory-graph", help="MCP server name (default: memory-graph)"
    )
    p_register.add_argument(
        "--token",
        default=None,
        help="CLAUDE_CODE_OAUTH_TOKEN value (default: read from env)",
    )
    p_register.add_argument(
        "--binary",
        default=None,
        help="absolute path to the memory-graph binary (default: auto-detect)",
    )
    p_register.add_argument(
        "--force",
        action="store_true",
        help="overwrite if an entry with this name already exists",
    )
    p_register.set_defaults(func=cmd_register)

    p_unreg = sub.add_parser(
        "unregister",
        help="remove this tool's entry from .mcp.json or ~/.claude.json",
    )
    p_unreg.add_argument(
        "--scope", choices=["project", "user"], default="project"
    )
    p_unreg.add_argument("--path", default=".")
    p_unreg.add_argument("--name", default="memory-graph")
    p_unreg.set_defaults(func=cmd_unregister)

    p_viz = sub.add_parser(
        "viz", help="serve a local web viewer for the memory graph"
    )
    p_viz.add_argument(
        "--path", default=None,
        help="project root containing .memory-graph/ (default: walk up from cwd)",
    )
    p_viz.add_argument("--port", type=int, default=8765)
    p_viz.add_argument("--host", default="127.0.0.1")
    p_viz.add_argument(
        "--no-browser", action="store_true",
        help="don't auto-open the browser",
    )
    p_viz.set_defaults(func=cmd_viz)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
