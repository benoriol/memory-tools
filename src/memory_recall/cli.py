"""memory-recall CLI: init / serve / status / viz / register / unregister /
install-claude-md / uninstall-claude-md / setup."""

from __future__ import annotations

import argparse
import json
import sys
from importlib import resources
from pathlib import Path
from typing import Any

from memory_recall.storage import STORE_DIRNAME
from memory_recall.storage.files import init_store, store_root

_CLAUDE_MD_BEGIN = "<!-- BEGIN memory-recall -->"
_CLAUDE_MD_END = "<!-- END memory-recall -->"


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


def _claude_md_path(args: argparse.Namespace) -> Path:
    return Path(args.dir).resolve() / "CLAUDE.md" if args.dir else Path.cwd() / "CLAUDE.md"


def _load_template() -> str:
    return resources.files("memory_recall.templates").joinpath(
        "claude_md_section.md"
    ).read_text()


def _wrap_section(body: str) -> str:
    return f"{_CLAUDE_MD_BEGIN}\n{body.rstrip()}\n{_CLAUDE_MD_END}\n"


def _find_section(text: str) -> tuple[int, int] | None:
    start = text.find(_CLAUDE_MD_BEGIN)
    if start == -1:
        return None
    end = text.find(_CLAUDE_MD_END, start)
    if end == -1:
        return None
    return (start, end + len(_CLAUDE_MD_END))


def _cmd_install_claude_md(args: argparse.Namespace) -> int:
    path = _claude_md_path(args)
    section = _wrap_section(_load_template())
    existing = path.read_text() if path.exists() else ""
    span = _find_section(existing)
    if span is not None and not args.force:
        print(f"memory-recall section already present in {path}; use --force to replace")
        return 1
    if span is not None:
        new_text = existing[: span[0]] + section + existing[span[1] :].lstrip("\n")
        action = "replaced"
    elif existing:
        sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        new_text = existing + sep + section
        action = "appended"
    else:
        new_text = section
        action = "created"
    path.write_text(new_text)
    print(f"{action} memory-recall section in {path}")
    return 0


def _cmd_uninstall_claude_md(args: argparse.Namespace) -> int:
    path = _claude_md_path(args)
    if not path.exists():
        print(f"no CLAUDE.md at {path}")
        return 0
    existing = path.read_text()
    span = _find_section(existing)
    if span is None:
        print(f"no memory-recall section found in {path}")
        return 0
    before = existing[: span[0]].rstrip("\n")
    after = existing[span[1] :].lstrip("\n")
    if before and after:
        new_text = before + "\n\n" + after
    else:
        new_text = (before + after).lstrip("\n")
    if new_text and not new_text.endswith("\n"):
        new_text += "\n"
    path.write_text(new_text)
    print(f"removed memory-recall section from {path}")
    return 0


def _cmd_setup(args: argparse.Namespace) -> int:
    """Bundle register + init + install-claude-md into one idempotent call.

    Each step's "already done" soft-failure is tolerated (prints
    "(continuing; ...)"); hard failures bubble up as exit 1.
    """
    steps: list[tuple[str, int]] = []

    if not args.skip_register:
        ns = argparse.Namespace(scope=args.scope, force=args.force)
        rc = _cmd_register(ns)
        if rc == 1:
            print("(continuing; register reports already-present without --force)")
            rc = 0
        steps.append(("register", rc))

    if not args.skip_init:
        ns = argparse.Namespace(dir=args.dir)
        rc = _cmd_init(ns)
        steps.append(("init", rc))

    if not args.skip_claude_md:
        ns = argparse.Namespace(dir=args.dir, force=args.force)
        rc = _cmd_install_claude_md(ns)
        if rc == 1:
            print("(continuing; install-claude-md reports already-present without --force)")
            rc = 0
        steps.append(("install-claude-md", rc))

    failed = [name for name, rc in steps if rc != 0]
    if failed:
        print(f"setup failed at: {', '.join(failed)}")
        return 1
    print("setup complete")
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

    s = sub.add_parser(
        "install-claude-md",
        help="append (or replace) the memory-recall operating section in CLAUDE.md",
    )
    s.add_argument("dir", nargs="?", default=None)
    s.add_argument("--force", action="store_true", help="replace an existing section")
    s.set_defaults(fn=_cmd_install_claude_md)

    s = sub.add_parser(
        "uninstall-claude-md",
        help="remove the memory-recall section from CLAUDE.md",
    )
    s.add_argument("dir", nargs="?", default=None)
    s.set_defaults(fn=_cmd_uninstall_claude_md)

    s = sub.add_parser(
        "setup",
        help="one-shot per-project bootstrap: register + init + install-claude-md",
    )
    s.add_argument("dir", nargs="?", default=None)
    s.add_argument("--scope", choices=["project", "user"], default="project")
    s.add_argument("--force", action="store_true")
    s.add_argument("--skip-register", action="store_true")
    s.add_argument("--skip-init", action="store_true")
    s.add_argument("--skip-claude-md", action="store_true")
    s.set_defaults(fn=_cmd_setup)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
