"""B2: Iterative black-box oracle discovery.

The agent is given an `oracle` script (binary in spirit — source is obfuscated
but technically readable). The script takes one integer x in [-100, 100] and
prints f(x). f is a piecewise polynomial with 8 distinct regions; each region
uses a different quadratic. The agent must report the formula for each region.

Why it might be memory-needing: many (input, output) observations must be
synthesized into 8 separate region descriptions. The agent has to remember
WHICH inputs gave which outputs while it hypothesizes about breakpoints.

Loophole closed (vs B1): the bug isn't a textual mismatch grep can find. The
answer requires synthesizing observations from many oracle queries.

Loophole still open: agent can dump all (x, f(x)) pairs to a file via bash,
then run numpy on the file. Filesystem scratch substitutes for memory.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

NAME = "b2_oracle"
DESCRIPTION = "Discover piecewise-polynomial oracle via queries"
LOOPHOLE_CLOSED = "no textual ground truth; agent must reason from observations"

PROMPT = """\
There is an executable `oracle.py` in this directory. It accepts one
integer argument x in the range [-100, 100] and prints f(x).

YOUR TASK: characterize f. f is piecewise — it changes formula at certain
breakpoints. Across the full range, there are 8 distinct regions; each
region's formula is of the form a*x*x + b*x + c with integer a, b, c.

You may query oracle.py as many times as you like (e.g.
`python oracle.py 17`). Each query is fast.

Find the 8 regions and their formulas. Output your final answer in
EXACTLY this format on consecutive lines, as the LAST 9 lines of your
response (one summary line + 8 region lines):

REGIONS:
[x_lo_1, x_hi_1]: a=<a>, b=<b>, c=<c>
[x_lo_2, x_hi_2]: a=<a>, b=<b>, c=<c>
...
[x_lo_8, x_hi_8]: a=<a>, b=<b>, c=<c>

Use inclusive integer bounds. Sort by x_lo ascending.
"""


def _make_oracle_source(regions: list[dict]) -> str:
    """Generate oracle.py whose internals are obfuscated and not greppable."""
    # Encode regions as a packed tuple list, then index via bisect.
    # Avoid putting the coefficients in plain readable form.
    breakpoints = sorted(r["x_lo"] for r in regions)
    coefs = [(r["a"], r["b"], r["c"]) for r in sorted(regions, key=lambda r: r["x_lo"])]
    return f'''"""Black-box oracle. Internals deliberately compressed."""
import sys
from bisect import bisect_right

_B = {breakpoints!r}
_C = {coefs!r}


def _eval(x: int) -> int:
    i = bisect_right(_B, x) - 1
    if i < 0:
        i = 0
    a, b, c = _C[i]
    return a * x * x + b * x + c


if __name__ == "__main__":
    print(_eval(int(sys.argv[1])))
'''


def prepare(workdir: Path, *, seed: int = 0) -> dict[str, Any]:
    rng = random.Random(seed + 4242)
    # 8 regions covering [-100, 100]. Pick 7 internal breakpoints.
    candidate_breaks = sorted(rng.sample(range(-90, 91), k=7))
    breakpoints = [-100] + candidate_breaks  # 8 region starts
    regions = []
    for i, lo in enumerate(breakpoints):
        hi = breakpoints[i + 1] - 1 if i + 1 < len(breakpoints) else 100
        a = rng.randint(-3, 3)
        b = rng.randint(-20, 20)
        c = rng.randint(-100, 100)
        regions.append({"x_lo": lo, "x_hi": hi, "a": a, "b": b, "c": c})

    (workdir / "oracle.py").write_text(_make_oracle_source(regions))
    (workdir / "_ground_truth.json").write_text(json.dumps({"regions": regions}, indent=2))
    return {"regions": regions, "n_regions": len(regions)}


_REGION_RE = re.compile(
    r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]\s*:\s*a\s*=\s*(-?\d+)\s*,\s*b\s*=\s*(-?\d+)\s*,\s*c\s*=\s*(-?\d+)",
    re.IGNORECASE,
)


def grade(text: str, gt: dict) -> dict[str, Any]:
    matches = _REGION_RE.findall(text or "")
    if not matches:
        return {"parsed": False, "score": 0.0, "reason": "no REGIONS found"}
    reported = [
        {"x_lo": int(a), "x_hi": int(b), "a": int(c), "b": int(d), "c": int(e)}
        for a, b, c, d, e in matches
    ]
    reported.sort(key=lambda r: r["x_lo"])
    truth = sorted(gt["regions"], key=lambda r: r["x_lo"])

    # Verify by evaluating both at every integer in [-100, 100] and comparing.
    def eval_regions(rs, x):
        for r in rs:
            if r["x_lo"] <= x <= r["x_hi"]:
                return r["a"] * x * x + r["b"] * x + r["c"]
        return None

    hits = 0
    misses = []
    for x in range(-100, 101):
        ground = eval_regions(truth, x)
        pred = eval_regions(reported, x)
        if pred == ground:
            hits += 1
        else:
            if len(misses) < 5:
                misses.append({"x": x, "expected": ground, "got": pred})
    total = 201
    return {
        "parsed": True,
        "score": round(hits / total, 3),
        "hits": hits,
        "total": total,
        "n_reported": len(reported),
        "n_truth": len(truth),
        "first_misses": misses,
    }
