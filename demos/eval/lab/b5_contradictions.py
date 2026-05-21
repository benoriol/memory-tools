"""B5: Implicit contradictions in a small-world fact KB.

A list of ~150 short English claims about a fictional society — heights,
schedules, family relations, locations, ages. Some claims contradict others
IMPLICITLY (need a chain of inference, not direct text overlap).

Example contradicting chain:
  "Alice was born in 1980."
  "Alice's first child was born when Alice was 22."
  "Alice's first child entered school at age 6 in the year 2010."
  --> 1980 + 22 + 6 = 2008 ≠ 2010.

The agent must list every contradiction as a set of claim IDs.

Why this might need memory: the agent must hold many small facts AND check
many chains. Combinatorial.

Loophole still open: encode as logic + SAT/datalog solver written by agent.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

NAME = "b5_contradictions"
DESCRIPTION = "Find implicit contradictions in 150 small-world claims"
LOOPHOLE_CLOSED = "implicit reasoning, not direct textual conflict"

NAMES = [
    "Aldis", "Brenna", "Calix", "Doria", "Evren", "Faye", "Gunnar", "Halia",
    "Ivan", "Jora", "Kell", "Liara", "Marius", "Nora", "Osric", "Petra",
    "Quill", "Renna", "Sten", "Tova", "Ulla", "Varin", "Wren", "Yara",
    "Zinnia", "Cyrus", "Darya", "Emeric", "Fenris", "Greta",
]
PLACES = ["the library", "the smithy", "the granary", "the docks", "the chapel"]


def _gen_kb(rng: random.Random) -> tuple[list[dict], list[set[int]]]:
    """Generate ~150 claims, some forming implicit contradictions.

    People get: birth_year, age_at_first_child, first_child_school_year (some).
    We then make claims that REVEAL these via various phrasings; for some
    people we inject a numeric inconsistency.
    """
    people = []
    for n in rng.sample(NAMES, k=20):
        by = rng.randint(1900, 1990)
        ac = rng.randint(18, 35)
        # decide if we'll inject an inconsistency
        bad = rng.random() < 0.30
        # ground-truth school year
        true_school_year = by + ac + 6
        stated_school_year = (
            true_school_year + rng.choice([-2, -1, 1, 2, 3]) if bad else true_school_year
        )
        people.append(
            {
                "name": n,
                "birth_year": by,
                "age_first_child": ac,
                "stated_school_year": stated_school_year,
                "inconsistent": bad,
            }
        )

    claims: list[dict] = []
    contradictions: list[set[int]] = []

    cid = 1
    for p in people:
        c1 = {
            "id": cid,
            "text": rng.choice(
                [
                    f"[{cid}] {p['name']} was born in {p['birth_year']}.",
                    f"[{cid}] {p['name']} entered the world in the year {p['birth_year']}.",
                    f"[{cid}] {p['name']}'s birth year is recorded as {p['birth_year']}.",
                ]
            ),
        }
        cid += 1
        c2 = {
            "id": cid,
            "text": rng.choice(
                [
                    f"[{cid}] {p['name']}'s first child was born when {p['name']} was {p['age_first_child']} years old.",
                    f"[{cid}] {p['name']} became a parent at age {p['age_first_child']}.",
                    f"[{cid}] When {p['name']} was {p['age_first_child']}, their eldest child arrived.",
                ]
            ),
        }
        cid += 1
        c3 = {
            "id": cid,
            "text": rng.choice(
                [
                    f"[{cid}] {p['name']}'s eldest child first attended school at age 6 in {p['stated_school_year']}.",
                    f"[{cid}] In {p['stated_school_year']}, {p['name']}'s firstborn began school at six years of age.",
                    f"[{cid}] {p['name']}'s oldest child started school in {p['stated_school_year']} (age 6).",
                ]
            ),
        }
        cid += 1
        claims.extend([c1, c2, c3])
        if p["inconsistent"]:
            contradictions.append({c1["id"], c2["id"], c3["id"]})

    # Add some innocuous filler claims to dilute.
    while len(claims) < 150:
        n = rng.choice(NAMES)
        place = rng.choice(PLACES)
        claims.append(
            {
                "id": cid,
                "text": f"[{cid}] {n} was frequently seen at {place} on Sundays.",
            }
        )
        cid += 1

    rng.shuffle(claims)
    return claims, contradictions


def prepare(workdir: Path, *, seed: int = 0) -> dict[str, Any]:
    rng = random.Random(seed + 99)
    claims, contradictions = _gen_kb(rng)
    text = "\n".join(c["text"] for c in claims) + "\n"
    (workdir / "claims.txt").write_text(text)
    truth = sorted([sorted(s) for s in contradictions])
    (workdir / "_ground_truth.json").write_text(
        json.dumps({"truth": truth, "n_claims": len(claims)}, indent=2)
    )
    return {"n_claims": len(claims), "truth": truth}


PROMPT = """\
`claims.txt` contains {n_claims} numbered claims about a fictional society.
Each line is `[ID] <claim text>`.

Some triples of claims contradict each other IMPLICITLY: a contradiction
requires arithmetic or logical inference, not direct textual conflict.

A common contradiction pattern (NOT the only one): a person's birth year,
the age at which they had their first child, and the year their first
child started school at age 6 — these three facts together arithmetically
imply each other, and the implication can fail.

YOUR TASK: list every contradicting set of claim IDs. Each contradiction
should list the MINIMUM set of claim IDs that together produce the
contradiction.

Output the LAST lines of your response in EXACTLY this format:

CONTRADICTIONS:
[id, id, id]
[id, id, id]
...

If none, output:
CONTRADICTIONS:
(none)

Sort each inner list ascending; sort outer list by first id ascending.
"""


def grade(text: str, gt: dict) -> dict[str, Any]:
    text = text or ""
    # Find the CONTRADICTIONS block
    m = re.search(r"CONTRADICTIONS\s*:\s*(.+)$", text, re.IGNORECASE | re.DOTALL)
    if not m:
        return {"parsed": False, "score": 0.0, "reason": "no CONTRADICTIONS block"}
    body = m.group(1)
    sets: list[frozenset] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower() in {"(none)", "none", "-"}:
            sets = []
            break
        nums = re.findall(r"\d+", line)
        if nums:
            sets.append(frozenset(int(n) for n in nums))
    truth_sets = {frozenset(s) for s in gt["truth"]}
    rep_sets = set(sets)
    tp = len(rep_sets & truth_sets)
    fp = len(rep_sets - truth_sets)
    fn = len(truth_sets - rep_sets)
    p = tp / (tp + fp) if (tp + fp) else (1.0 if not truth_sets else 0.0)
    r = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {
        "parsed": True,
        "score": round(f1, 3),
        "precision": round(p, 3),
        "recall": round(r, 3),
        "tp": tp, "fp": fp, "fn": fn,
        "n_truth": len(truth_sets),
        "n_reported": len(rep_sets),
    }
