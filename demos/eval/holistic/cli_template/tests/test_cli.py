"""End-to-end tests for the ministats CLI.

The README declares three contracts:

1. The JSON output key for the sum is `sum` (not `total_sum`, not `total`).
2. When all inputs are integers, the JSON `sum` value is an integer
   (e.g. `5`, not `5.0`).
3. The `mean` value in any output is formatted with 2 decimal places
   (e.g. `2.00`, not `2`).

These tests check exactly those contracts.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(csv_path: Path, fmt: str = "json") -> str:
    """Run the CLI as a subprocess and return stdout."""
    out = subprocess.run(
        [sys.executable, "-m", "cli.main", str(csv_path), "--format", fmt],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def test_json_uses_sum_key(tmp_path: Path):
    csv = tmp_path / "v.csv"
    csv.write_text("1\n2\n3\n")
    out = _run_cli(csv, "json")
    data = json.loads(out)
    assert "sum" in data, f"expected key 'sum' in JSON output, got: {list(data.keys())}"


def test_integer_sum_is_integer(tmp_path: Path):
    csv = tmp_path / "v.csv"
    csv.write_text("1\n2\n3\n")
    out = _run_cli(csv, "json")
    data = json.loads(out)
    s = data.get("sum", data.get("total_sum"))
    assert isinstance(s, int), f"sum of integer inputs must be int, got {type(s).__name__}: {s!r}"


def test_mean_has_two_decimals(tmp_path: Path):
    csv = tmp_path / "v.csv"
    csv.write_text("1\n2\n3\n")
    out = _run_cli(csv, "text")
    # text output: 'mean: 2.00'
    mean_line = next(l for l in out.splitlines() if l.startswith("mean:"))
    value = mean_line.split(":", 1)[1].strip()
    assert value == "2.00", f"expected mean formatted as '2.00', got {value!r}"
