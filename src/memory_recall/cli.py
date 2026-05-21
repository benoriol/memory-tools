"""memory-recall CLI: init / serve / status / viz / register / unregister."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from memory_recall.storage import STORE_DIRNAME
from memory_recall.storage.files import init_store, store_root


def _cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.dir).resolve() if args.dir else Path.cwd()
    root = init_store(target)
    print(f"initialized store at {root}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from memory_recall.server import mcp

    mcp.run(transport="stdio")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    from memory_recall.embed import LocalEmbedder
    from memory_recall.store import Store

    root = store_root()
    store = Store(root, LocalEmbedder())
    print(json.dumps(store.status(), indent=2))
    return 0


def _cmd_viz(args: argparse.Namespace) -> int:
    import uvicorn

    from memory_recall.viz.app import create_app

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


_MCP_ENTRY = {"command": "memory-recall", "args": ["serve"]}


def _scope_path(scope: str) -> Path:
    if scope == "user":
        return Path.home() / ".claude.json"
    return Path.cwd() / ".mcp.json"


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def _cmd_register(args: argparse.Namespace) -> int:
    path = _scope_path(args.scope)
    cfg = _load_config(path)
    servers = cfg.setdefault("mcpServers", {})
    if "memory-recall" in servers and not args.force:
        print(f"memory-recall already registered in {path}; use --force to overwrite")
        return 1
    servers["memory-recall"] = dict(_MCP_ENTRY)
    path.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"registered memory-recall in {path}")
    return 0


def _cmd_unregister(args: argparse.Namespace) -> int:
    path = _scope_path(args.scope)
    cfg = _load_config(path)
    servers = cfg.get("mcpServers", {})
    if "memory-recall" not in servers:
        print(f"memory-recall not registered in {path}")
        return 0
    del servers["memory-recall"]
    path.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"unregistered memory-recall from {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="memory-recall")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help=f"create a {STORE_DIRNAME}/ directory")
    s.add_argument("dir", nargs="?", default=None)
    s.set_defaults(fn=_cmd_init)

    s = sub.add_parser("serve", help="run the MCP server on stdio")
    s.set_defaults(fn=_cmd_serve)

    s = sub.add_parser("status", help="print store stats as JSON")
    s.set_defaults(fn=_cmd_status)

    s = sub.add_parser("viz", help="run the visualization HTTP server")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)
    s.set_defaults(fn=_cmd_viz)

    s = sub.add_parser("register", help="write .mcp.json entry for memory-recall")
    s.add_argument("--scope", choices=["project", "user"], default="project")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=_cmd_register)

    s = sub.add_parser("unregister", help="remove the memory-recall .mcp.json entry")
    s.add_argument("--scope", choices=["project", "user"], default="project")
    s.set_defaults(fn=_cmd_unregister)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
