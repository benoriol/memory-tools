Capture a knowledge note: durable methodology, a fact, or a gotcha. Content or instruction: $ARGUMENTS

Record durable operational knowledge in the knowledge store as a leaf in a topic folder, then
refresh the index. This is not a dated result (that is `/mem-log`) and not the project story
(that is `/mem-canon`).

**1. New note or edit?** Read `knowledge/index.md` and decide whether this extends an existing
note or opens a new topic. Editing an existing note mutates durable truth, so it is gated
harder than adding one.

**2. Choose placement.** Pick the folder path under `knowledge/` (e.g. `arch/caching/`).
Placement gating:
- a new leaf under an existing folder: low, just confirm the path.
- a new subfolder: medium, name it and confirm before creating.
- a new top-level topic: medium-high, confirm the taxonomy choice first.
Keep the tree shallow and purposeful; do not invent deep nesting for a single note.

**3. Shallow consistency check (before writing).** Read the directly-related note(s) and any
recipe, default, or claim this asserts that also appears in a journal leaf or `canon/`. If it
contradicts a recorded default, duplicates an existing note, or supersedes one, push back and
say what conflicts and where before finalizing.

**A. New note (low friction).** Write `knowledge/<path>/<slug>.md`: H1 `# <Title>`, then
`**Summary:** <one line>` (what the index shows), then terse bullets or short sections. Include
code, paths, and flags where they prevent mistakes. Link to related leaves; do not restate
knowledge that already lives elsewhere. Never put always-on, mistake-preventing rules here;
those belong in the spine / `CLAUDE.md`.

**B. Edit an existing note (medium friction).** Read the target in full, show the proposed diff
(or a tight before/after), and wait for approval before writing. Make the minimal change; do
not restructure unasked. Update the `**Summary:**` line only if the scope shifted.

**4. Refresh the index.** Run `/mem-index knowledge`.

**Always:** keep the index-to-leaf split (the index points and summarizes, the leaf holds the
depth); never invent numbers or paths, write "TBD" instead; if the knowledge looks
canon-worthy, suggest `/mem-canon`, never write `canon/` here.
