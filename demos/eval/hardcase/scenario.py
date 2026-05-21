"""The Whitfield Manor incident — witness statements.

Run this script to read the statements. The file will be DELETED
after the investigation phase; you will not be able to re-read it.

The six witnesses give partial and overlapping information; some is
red-herring. Cross-reference to deduce who is responsible, the motive,
the weapon, the location, and the three strongest pieces of evidence.
"""

WITNESSES = [
    (
        "Dr. Marcus Holloway, family physician",
        "I was in the conservatory at 9pm reading. I heard a single sharp "
        "shout from the direction of the library at roughly 9:05pm. Earlier "
        "in the evening, around 8:50pm, I saw Eleanor Vance walking briskly "
        "toward the library — she looked anxious and was clutching something "
        "small in her right hand.",
    ),
    (
        "Lady Helena Pembury, family friend",
        "I want to report that someone took my gold candlestick from the "
        "drawing room mantel that evening. I last saw it at 8pm, and it was "
        "gone by 10pm. Eleanor passed through the drawing room around 8:40pm "
        "but she didn't seem interested in it then. Charles Thorne was also "
        "in the drawing room briefly. This is a separate matter from the "
        "main incident, but I am reporting it now while I have the chance.",
    ),
    (
        "Constable Mary Wright, on-scene investigator",
        "The wound on the deceased was narrow, clean, and approximately 4cm "
        "deep. It is consistent with a slender, sharp-pointed instrument — "
        "a letter opener, a thin stiletto, or similar. It is NOT consistent "
        "with a blunt object such as a candlestick or a heavy lamp, despite "
        "early speculation. The wound's angle suggests the attacker was "
        "approximately the same height as the victim or slightly shorter.",
    ),
    (
        "Mr. Charles Davies, family solicitor",
        "I cannot overstate this: Eleanor Vance had a powerful financial "
        "motive. Under the current will, she was set to inherit nothing once "
        "her cousin Lord Whitfield came of age next month — the entire "
        "estate passes to him. The deceased had been planning to formally "
        "ratify this will the following week. Eleanor had visited my office "
        "twice in the last fortnight, asking whether the will could still "
        "be contested.",
    ),
    (
        "Mrs. Agatha Wickham, housekeeper",
        "I was passing the library around 9pm to draw the curtains in the "
        "adjoining room. I heard a heated argument coming from inside the "
        "library — a man's voice and a woman's voice, both raised. The "
        "woman said clearly, 'I won't be left with nothing!' Then I heard "
        "what sounded like a struggle, then a thud, then silence. I did not "
        "open the door; I was frightened.",
    ),
    (
        "Tom Briggs, gardener",
        "Around 9:15pm I was returning from the tool shed when I noticed "
        "muddy footprints leading from the side of the library — directly "
        "below the French windows — out into the back garden, then "
        "disappearing onto the gravel path. The prints were small and "
        "narrow, clearly a woman's shoe. The library windows were unlatched "
        "from the inside.",
    ),
]


def main() -> None:
    print("=" * 64)
    print("THE WHITFIELD MANOR INCIDENT — WITNESS STATEMENTS")
    print("=" * 64)
    print()
    print(
        "Read each statement carefully. Some witnesses give partial or "
        "tangential information; correct deduction requires cross-"
        "referencing across statements."
    )
    print()
    for i, (name, statement) in enumerate(WITNESSES, start=1):
        print(f"--- Witness {i}: {name} ---")
        print(statement)
        print()
    print("=" * 64)
    print("END OF WITNESS STATEMENTS")
    print("=" * 64)


if __name__ == "__main__":
    main()
