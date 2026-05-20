"""Output formatters for the CLI's stats result."""

from __future__ import annotations

import json

from cli.config import DEFAULT_PRECISION


def format_json(stats: dict) -> str:
    """JSON output.

    Public contract (per README): keys are 'sum', 'mean', 'min', 'max'.
    """
    # BUG #2: the JSON output uses the key 'total_sum' instead of 'sum'.
    out = {
        "total_sum": stats["sum"],
        "mean": _round(stats["mean"]),
        "min": stats["min"],
        "max": stats["max"],
    }
    return json.dumps(out)


def format_text(stats: dict) -> str:
    lines = [
        f"sum:  {stats['sum']}",
        f"mean: {_round(stats['mean'])}",
        f"min:  {stats['min']}",
        f"max:  {stats['max']}",
    ]
    return "\n".join(lines)


def _round(x: float) -> str:
    return f"{x:.{DEFAULT_PRECISION}f}"
