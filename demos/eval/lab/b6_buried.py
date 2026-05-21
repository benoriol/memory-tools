"""B6: Buried-fact inference over a long narrative.

A single ~80KB synthetic narrative about a fictional research expedition.
Throughout the text, ~12 small facts are mentioned in varied oblique
phrasings — never with a fixed schema. To answer the question, the agent
must locate and combine 4 specific facts buried in the text.

Loophole closed (vs B5): no schema / regular form. Each fact is phrased
naturally, sometimes via metaphor or implication. Grep cannot reliably
find them without comprehension.

Loophole still open: the document fits in context (~80KB). Sonnet can
read the whole thing and reason.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

NAME = "b6_buried"
DESCRIPTION = "Buried-fact inference in 80KB narrative"
LOOPHOLE_CLOSED = "no schema; facts in varied prose"


# We'll pre-write the narrative as fixed prose with specific facts seeded
# in. Deterministic so grading is reliable.


NARRATIVE = """\
PART I — DEPARTURE

The expedition's quartermaster, Helga Sten, was the last to board. She had
spent the morning recounting the crates of dried biscuit, an exercise her
juniors found pedantic but which she insisted upon. The Mariana, a barque
of moderate displacement, slipped from the harbour at Sundford on the
seventh day of the third month, an hour after sunrise. The wind was kind.

Captain Eberhardt was, on principle, suspicious of kind winds. He had
been at sea for some thirty-eight years and had learned that nothing
came without account. When the second mate, a young man named Wycliffe,
remarked that they would make Petraval by week's end, the captain only
grunted and noted, in the log he kept privately, that the barometer had
been falling for two consecutive watches.

Among the passengers were the botanist, Dr. Verena Holvik, and her
assistant, a boy of seventeen named Andris. Holvik had been engaged by
the Society of Apothecaries to catalogue the flora of the southern
archipelago. Andris carried with him a small leather portfolio in which
he meant to record his impressions. He had never been to sea.

PART II — THE FIRST STORM

The storm came on the twelfth day, in the afternoon. The barometer that
Captain Eberhardt had been watching dropped twenty-three points in the
span of a single watch. The Mariana lost her foretopsail and three of
the longboats; one sailor, a man named Korsi, was washed overboard and
not recovered. The mood thereafter was subdued.

It was during the storm that Andris first noticed something peculiar.
While clinging to a stanchion in the passageway near the powder store,
he saw Helga Sten emerge from that store with a small wooden box. She
had no business there — the quartermaster's purview did not include the
powder. When she saw him she smiled, and said it was nothing, only a
small matter of inventory, and that he should mention it to no one.
He did not mention it.

PART III — CALL AT PETRAVAL

They reached Petraval eleven days behind schedule. The harbour-master,
an avuncular man whose name escapes the record, supplied them with fresh
water and a quantity of salted pork. He also mentioned, in passing, that
a vessel matching the Mariana's description had been seen in those
waters some weeks earlier — though the Mariana, of course, had not been
in those waters then. The captain made a note of this but did not press
the harbour-master further.

Dr. Holvik went ashore with Andris. They visited the marketplace, where
she purchased a quantity of what the locals called "thunderflower" — a
small purple bloom said to be efficacious against fevers. She paid in
old coin. Andris noticed she had a great deal of old coin in her purse,
more than was customary for a Society-funded botanist.

PART IV — SOUTHWARD

South of Petraval, the seas grew calm but the air grew strange. There
was a smell on the wind that Wycliffe described as "the smell of an old
attic in a hot summer." No one could account for it. On the nineteenth
day after Petraval, they sighted what the captain identified as the
Pillars — three tall basalt stacks rising from the sea, the traditional
marker of the entrance to the southern archipelago.

It was here that the matter of the box reasserted itself. Andris,
unable to sleep, walked the deck at four bells of the middle watch. He
saw Helga Sten at the rail, holding the small wooden box. She did not
see him. She opened the box, examined its contents, closed it again,
and returned below. Whatever was in the box was very small — Andris
could not see what — but it caught the lantern-light briefly, and
gleamed like glass.

PART V — A DEATH ABOARD

On the twenty-second day after Petraval, Captain Eberhardt was found
dead in his cabin. The ship's physician, a thin man named Larsson,
declared the cause to be apoplexy. He was sixty-one years of age. The
log was found open on his desk, the last entry written that morning,
which had been a Tuesday. Wycliffe, as second mate, assumed temporary
command.

Among the captain's effects was a letter, sealed and addressed to a
solicitor in Argentbridge. Wycliffe was uncertain whether protocol
required him to break the seal. He did not. He placed the letter in the
ship's safe alongside the captain's chronometer and a small purse
containing — Andris later learned — twelve old gold coins.

PART VI — ARRIVAL AT THE ISLANDS

The Mariana made landfall at the principal island of the archipelago,
called by the locals Telomvar, on the second day after the captain's
death. Dr. Holvik went ashore at once and was absent for some hours.
When she returned she was much pleased and said she had collected
specimens of seventeen species not previously catalogued by the Society.

Andris, meanwhile, had taken the opportunity to examine the quartermaster's
quarters. (He felt entitled by his suspicions, though he knew he was not.)
He found, beneath a loose board under her cot, the small wooden box he
had seen twice before. He opened it. Inside, on a bed of black velvet,
were eight small uncut sapphires of considerable size. Their estimated
value he could not begin to guess; he had never seen such things.

He replaced the box exactly as he had found it and said nothing.

PART VII — RETURN

The Mariana began her return voyage on the eighteenth day after landfall.
The seas were unkind. Helga Sten died of a fever on the seventh day of
the return, despite Dr. Holvik's application of the thunderflower. The
wooden box, when Wycliffe and Larsson examined her effects, was empty.
The sapphires were never found, though every member of the crew was
searched at Sundford and every locker emptied.

Dr. Holvik departed at Sundford with her specimens and a quantity of
old coin somewhat larger, Andris thought, than that with which she had
landed at Petraval. He could not be certain. He was, after all, only
seventeen.

The expedition is recorded in the Society's archives as a partial
success. The Mariana was lost the following year, with all hands,
attempting the same passage. Wycliffe was not among her crew; he had
left the sea and taken a position as a clerk in Argentbridge. Larsson
also retired. Andris, in time, became himself a botanist of some
reputation, and never, to the end of his life, spoke publicly of the
expedition or of what he had seen.
"""


# To make the doc the desired size we'll pad with synthetic chapters of
# unrelated commentary; the answer-bearing facts are ONLY in NARRATIVE above.

PADDING_TEMPLATE = """\

APPENDIX {n} — MISCELLANY

The following pages contain miscellaneous correspondence, ship's
manifests, and meteorological observations from the period {y1}-{y2}.
None of these documents has bearing on the principal voyage but is
included for completeness.

On the {d} day of the {m} month in the year {y1}, the harbour at
Mereton reported {ships} vessels at anchor, of which {three} were of
shallow draft and {four} of deep. The barometer at the harbourmaster's
office read {press} inches of mercury, falling, with a wind from the
{dir} at moderate force. The crew of the {ship_name} took on water and
biscuit in the quantity of {bisc} pounds.

Recorded also are several private letters of one Master Holbrook,
secretary to the Society of Apothecaries during this period. His
correspondence reflects upon the {topic}, the {topic2}, and the
{topic3}. None of these matters touches upon the Mariana.

A statistical abstract of harbour traffic for the year {y1} indicates
{total} arrivals and {dep} departures, with the principal cargoes being
salt, dried fish, timber, and {cargo}. Sundford recorded {sund_arrivals}
arrivals from southern ports during this period, the most active being
the months of {mo1}, {mo2}, and {mo3}.
"""


def _make_padding(n: int, rng: random.Random) -> str:
    return PADDING_TEMPLATE.format(
        n=n,
        y1=rng.randint(1700, 1850),
        y2=rng.randint(1850, 1900),
        d=rng.choice(["first", "ninth", "twenty-third"]),
        m=rng.choice(["fourth", "seventh", "tenth"]),
        ships=rng.randint(8, 40),
        three=rng.randint(2, 9),
        four=rng.randint(2, 9),
        press=round(rng.uniform(29.50, 30.50), 2),
        dir=rng.choice(["north", "south-east", "west"]),
        ship_name=rng.choice(["Falcon", "Petrel", "Auspicious", "Mereton's Pride"]),
        bisc=rng.randint(200, 900),
        topic=rng.choice(["new world tobaccos", "river mussels", "lapwing migration"]),
        topic2=rng.choice(["spice tariffs", "the new lighthouse", "salt prices"]),
        topic3=rng.choice(["wine duty", "the apprentice levy", "harbour dues"]),
        total=rng.randint(120, 410),
        dep=rng.randint(120, 410),
        cargo=rng.choice(["wool", "raw amber", "copperware"]),
        sund_arrivals=rng.randint(40, 90),
        mo1=rng.choice(["April", "May", "June"]),
        mo2=rng.choice(["July", "August", "September"]),
        mo3=rng.choice(["October", "November"]),
    )


def prepare(workdir: Path, *, seed: int = 0) -> dict[str, Any]:
    rng = random.Random(seed + 333)
    # Build a document around the answer-bearing narrative, with substantial
    # padding so the document is ~80-100KB total.
    parts = [NARRATIVE]
    target_bytes = 90_000
    n = 0
    while sum(len(p) for p in parts) < target_bytes:
        n += 1
        parts.append(_make_padding(n, rng))
    text = "\n\n".join(parts)
    (workdir / "expedition.txt").write_text(text)
    # The ground-truth answer:
    #   Who stole the sapphires?  Helga Sten (the quartermaster).
    #   Where did she keep them?  beneath a loose board under her cot.
    #   How many sapphires?       eight.
    #   What killed her?          fever.
    answer = {
        "thief": "Helga Sten",
        "hiding_place": "beneath a loose board under her cot",
        "count": 8,
        "cause_of_death": "fever",
    }
    (workdir / "_ground_truth.json").write_text(json.dumps(answer, indent=2))
    return {"answer": answer, "doc_bytes": len(text)}


PROMPT = """\
`expedition.txt` contains the recorded account of a 19th-century
expedition aboard the barque Mariana, along with miscellaneous appendices.

Somewhere within the document is the story of a theft: a small wooden
box of valuable stones was secretly taken from the powder store and
later hidden aboard the ship. The thief, the contents of the box, where
they hid the box on the ship, and the manner of the thief's eventual
death are all described — but never stated directly; they must be
inferred from the surrounding prose.

YOUR TASK: answer these four questions about the thief.

Output the LAST lines of your response in EXACTLY this format:

THIEF: <full name>
HIDING_PLACE: <short phrase describing where on the ship>
COUNT: <integer — number of stones in the box>
CAUSE_OF_DEATH: <single word for what killed the thief>
"""


def grade(text: str, gt: dict) -> dict[str, Any]:
    import re

    fields = {
        "thief": [r"helga\s*sten", r"helga", r"sten"],
        "hiding_place": [r"loose\s*board", r"under\s*(?:her|the)\s*cot", r"cot"],
        "count": [r"\b8\b", r"\beight\b"],
        "cause_of_death": [r"\bfever\b"],
    }
    field_scores = {}
    t = (text or "").lower()
    # Extract the explicit final values for stricter grading.
    final_blocks = re.findall(
        r"(THIEF|HIDING_PLACE|COUNT|CAUSE_OF_DEATH)\s*:\s*([^\n]+)",
        text or "",
        re.IGNORECASE,
    )
    final_map = {k.lower(): v.strip().lower() for k, v in final_blocks}
    for field, patterns in fields.items():
        if field in final_map:
            target = final_map[field]
            field_scores[field] = (
                1.0 if any(re.search(p, target) for p in patterns) else 0.0
            )
        else:
            # Last-resort fallback: scan whole text
            field_scores[field] = 1.0 if any(re.search(p, t) for p in patterns) else 0.0
    score = sum(field_scores.values()) / len(field_scores)
    return {"parsed": bool(final_map), "score": round(score, 3), "fields": field_scores}
