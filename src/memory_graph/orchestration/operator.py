"""Operator-context file management.

`_operator/context.md` lives inside the project store. It's the
sub-agent's hand-curated working knowledge of the graph (clusters,
hubs, learned heuristics). Updated manually for v0; auto-update via
the sub-agent comes in v1.
"""

from __future__ import annotations

from pathlib import Path

OPERATOR_DIRNAME = "_operator"
OPERATOR_FILE = "context.md"

_DEFAULT_TEMPLATE = """# Operator context

This file is the memory sub-agent's working knowledge of the graph.
Edit freely; the sub-agent reads it at the start of every operation.

## Graph map

(empty — populate as clusters and hubs emerge)

## Heuristics

(none yet)

## Open items

(none yet)
"""


def operator_path(store_root: str | Path) -> Path:
    return Path(store_root) / OPERATOR_DIRNAME / OPERATOR_FILE


def read_operator_context(store_root: str | Path) -> str:
    """Return the operator-context text, creating a default if missing."""
    p = operator_path(store_root)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_DEFAULT_TEMPLATE, encoding="utf-8")
        return _DEFAULT_TEMPLATE
    return p.read_text(encoding="utf-8")


def write_operator_context(store_root: str | Path, content: str) -> Path:
    """Overwrite the operator-context file. Returns the path."""
    p = operator_path(store_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p
