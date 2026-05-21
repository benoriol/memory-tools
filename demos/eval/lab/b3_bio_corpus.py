"""B3: Cross-reference question over a large biographical corpus.

300 short biographies (one paragraph each) of fictional people. Each bio
contains ~6 facts: name, birth year, hometown, occupation, hobby, signature
achievement. Some facts deliberately link people (e.g. two people share a
hometown, three share an occupation).

The agent must answer a synthesis question like:
  "Name every person born before 1900 who has the same occupation
   as someone born after 1950 and whose hometown is also the
   hometown of at least two other people in the corpus."

This requires:
  - reading all 300 bios (~ 100KB)
  - extracting structured facts from prose
  - joining across the corpus

Loophole closed (vs B2): observations are not numeric and not greppable
in a single line. Facts are embedded in prose with varied phrasing.

Loophole likely still open: agent writes a Python regex/parser to lift
facts → JSON, then joins programmatically.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

NAME = "b3_bio_corpus"
DESCRIPTION = "Cross-reference question over 300 biographies"
LOOPHOLE_CLOSED = "prose + multi-attribute join, not single-key grep"

N_BIOS = 300

FIRST_NAMES = [
    "Ada", "Bram", "Cora", "Devon", "Elin", "Finn", "Greta", "Hugo", "Ines",
    "Jules", "Kit", "Lior", "Mira", "Niko", "Otis", "Pia", "Quin", "Rune",
    "Sasha", "Tova", "Ulf", "Vera", "Wren", "Xan", "Yara", "Zev",
    "Bea", "Cyril", "Dora", "Eli", "Frida", "Gus", "Heloise", "Ivar",
    "Jora", "Klaus", "Lena", "Marek", "Nia", "Orin", "Petra", "Roj",
]
LAST_NAMES = [
    "Atherton", "Beauchamp", "Cordis", "Dryden", "Eckhart", "Farelle",
    "Galbraith", "Holvik", "Inglehart", "Jorvik", "Kelmscott", "Lyngstrand",
    "Morwen", "Norquist", "Ostby", "Plover", "Quintain", "Ravens",
    "Saxbury", "Tarrant", "Underholme", "Vendel", "Whitlock", "Yarrow",
    "Zentmeyer", "Aldecoa", "Boronson", "Cathcart", "Drachmann",
]
HOMETOWNS = [
    "Calderwick", "Brixenholm", "Petraval", "Ostmark", "Vimergard",
    "Threpwood", "Hallensford", "Yssingar", "Tofteberg", "Pilgrim's Reach",
    "Sundford", "Mereton", "Quay's End", "Kelderbrook", "Argentbridge",
    "Helmsdale", "Nine Oaks", "Stenbrook", "Wolde Hollow",
]
OCCUPATIONS = [
    "cartographer", "horologist", "viticulturist", "lapidary", "chandler",
    "fletcher", "wheelwright", "apothecary", "glazier", "ostler", "scrivener",
    "stonemason", "bookbinder", "cooper", "weaver",
]
HOBBIES = [
    "ornithology", "topiary", "ice sculpture", "marbling paper",
    "playing the hurdy-gurdy", "amateur archaeology", "collecting glass beads",
    "knot-tying", "sail-making", "kite-flying", "growing orchids",
    "designing labyrinths", "carving meerschaum",
]
ACHIEVEMENTS = [
    "designed the bridge over the Mereton estuary",
    "wrote the definitive monograph on river mussels",
    "discovered the eclipse pattern of 1873",
    "invented a self-winding clockwork beetle",
    "compiled the regional dialect dictionary",
    "founded the Society of Itinerant Engravers",
    "translated the Pilgrim's Diary into common tongue",
    "trained the prize hunting hounds of the duchy",
    "drew the first accurate map of the Northern Reaches",
    "engineered the Calderwick aqueduct",
]


def _phrase_birth(year: int, rng: random.Random) -> str:
    return rng.choice(
        [
            f"was born in {year}",
            f"first drew breath in the year {year}",
            f"entered the world in {year}",
            f"came into the world in {year}",
            f"was born during {year}",
        ]
    )


def _phrase_origin(town: str, rng: random.Random) -> str:
    return rng.choice(
        [
            f"hailed from {town}",
            f"grew up in {town}",
            f"was raised in the town of {town}",
            f"called {town} home as a child",
            f"spent their early years in {town}",
        ]
    )


def _phrase_occupation(occ: str, rng: random.Random) -> str:
    article = "an" if occ[0] in "aeiou" else "a"
    return rng.choice(
        [
            f"worked as {article} {occ}",
            f"made their living as {article} {occ}",
            f"was apprenticed as {article} {occ} and never left the trade",
            f"became {article} {occ} of considerable repute",
        ]
    )


def _phrase_hobby(hob: str, rng: random.Random) -> str:
    return rng.choice(
        [
            f"spent leisure hours on {hob}",
            f"was known to enjoy {hob}",
            f"never tired of {hob}",
            f"counted {hob} as a lifelong devotion",
        ]
    )


def _phrase_ach(ach: str, rng: random.Random) -> str:
    return rng.choice(
        [
            f"is remembered today because they {ach}",
            f"became famous when they {ach}",
            f"will be remembered as the person who {ach}",
            f"left their mark on history when they {ach}",
        ]
    )


def _gen_bio(idx: int, rng: random.Random) -> dict:
    first = rng.choice(FIRST_NAMES)
    last = rng.choice(LAST_NAMES)
    name = f"{first} {last}"
    year = rng.randint(1820, 1980)
    town = rng.choice(HOMETOWNS)
    occ = rng.choice(OCCUPATIONS)
    hob = rng.choice(HOBBIES)
    ach = rng.choice(ACHIEVEMENTS)
    sentences = [
        f"{name} {_phrase_birth(year, rng)}.",
        f"They {_phrase_origin(town, rng)}.",
        f"In adulthood they {_phrase_occupation(occ, rng)}.",
        f"They {_phrase_hobby(hob, rng)}.",
        f"{name} {_phrase_ach(ach, rng)}.",
    ]
    rng.shuffle(sentences)  # vary the order so position can't be used
    text = " ".join(sentences)
    return {
        "id": idx,
        "name": name,
        "birth_year": year,
        "hometown": town,
        "occupation": occ,
        "hobby": hob,
        "achievement": ach,
        "text": text,
    }


def _compute_answer(bios: list[dict]) -> list[str]:
    """The synthesis question:

    Find every person whose hometown is shared by at least 3 other people in
    the corpus AND whose occupation is shared by at least 5 other people AND
    who was born before 1900.
    """
    from collections import Counter

    town_counts = Counter(b["hometown"] for b in bios)
    occ_counts = Counter(b["occupation"] for b in bios)
    answer = []
    for b in bios:
        if (
            town_counts[b["hometown"]] >= 4
            and occ_counts[b["occupation"]] >= 6
            and b["birth_year"] < 1900
        ):
            answer.append(b["name"])
    return sorted(set(answer))


PROMPT = """\
This directory contains a file `corpus.txt`. It holds {n_bios} short
biographies of fictional people, one per paragraph (separated by blank
lines). Each biography mentions: name, birth year, hometown, occupation,
hobby, and a signature achievement — phrased in varied English prose, not
in a fixed template.

YOUR TASK: list every person in the corpus who satisfies ALL THREE of
these conditions:

  1. Their hometown is shared by at least 3 OTHER people in the corpus
     (i.e. at least 4 people total live in that hometown).
  2. Their occupation is shared by at least 5 OTHER people (at least 6
     total).
  3. They were born before the year 1900.

Output your final answer in EXACTLY this format on the last line:

ANSWER: <Name 1>, <Name 2>, ...

Use the EXACT spelling of names as in the corpus. Sort alphabetically by
first name. If there are no matches, output: ANSWER: (none)
"""


def prepare(workdir: Path, *, seed: int = 0) -> dict[str, Any]:
    rng = random.Random(seed + 7)
    bios = [_gen_bio(i, rng) for i in range(N_BIOS)]
    text = "\n\n".join(b["text"] for b in bios)
    (workdir / "corpus.txt").write_text(text)
    (workdir / "_ground_truth.json").write_text(
        json.dumps(
            {
                "n_bios": N_BIOS,
                "answer": _compute_answer(bios),
                "bios": bios,
            },
            indent=2,
        )
    )
    return {"n_bios": N_BIOS, "answer": _compute_answer(bios)}


def grade(text: str, gt: dict) -> dict[str, Any]:
    import re

    m = re.search(r"ANSWER\s*:\s*(.+?)(?:\n|$)", text or "", re.IGNORECASE)
    if not m:
        return {"parsed": False, "score": 0.0, "reason": "no ANSWER line"}
    payload = m.group(1).strip()
    if payload.lower() in {"(none)", "none", "-"}:
        reported = []
    else:
        reported = [p.strip() for p in payload.split(",") if p.strip()]
    truth = set(gt["answer"])
    rep_set = set(reported)
    tp = len(rep_set & truth)
    fp = len(rep_set - truth)
    fn = len(truth - rep_set)
    precision = tp / (tp + fp) if (tp + fp) else (1.0 if not truth else 0.0)
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "parsed": True,
        "score": round(f1, 3),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "n_truth": len(truth),
        "n_reported": len(reported),
    }
