"""CLI entry: read CSV → compute stats → format."""

from __future__ import annotations

import sys
from pathlib import Path

from cli.compute import stats
from cli.output import format_json, format_text
from cli.parser import build_parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = _load_csv(Path(args.path))
    result = stats(rows)
    if args.format == "json":
        print(format_json(result))
    else:
        print(format_text(result))
    return 0


def _load_csv(path: Path) -> list[float]:
    """Read a one-column CSV of floats. Treats integer-looking strings as int."""
    out: list[float] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Integer-looking values stay int; floats stay float.
        try:
            out.append(int(line))
        except ValueError:
            out.append(float(line))
    return out


if __name__ == "__main__":
    sys.exit(main())
