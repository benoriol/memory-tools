Capture a technical / methodology note: durable methodology, an operational fact, or a gotcha. Content or instruction: $ARGUMENTS

Record durable operational or methodology knowledge (architecture, loss/algorithm design,
evaluation protocol, running / tracking conventions, a recurring gotcha) as a leaf under
`technical_notes/`, then refresh its index. This is **not** a per-run result (that is `/logexp`)
and **not** a paper claim (that is `/papernote`). Research analog of `/mem-note`.

**1. New note or edit?** Read `technical_notes.md` (the index) and decide whether this extends an
existing note or opens a new topic. Editing an existing note mutates durable truth, so it is
gated harder than adding one.

**2. Shallow consistency check (before writing).** Read the directly-related note(s) and any
recipe default, number, or claim this asserts that also appears in an experiment leaf or
`paper_narrative.md`. If it contradicts a recorded default, duplicates an existing note, or
supersedes one, push back and say what conflicts and where before finalizing.

**A. New note (low friction).** Write `technical_notes/<slug>.md` (kebab slug, unique): H1
`# <Title>`, then `**Summary:** <one line>` (what the index shows), then terse bullets or short
sections. Include code, paths, and flags where they prevent mistakes. Link to related leaves; do
not restate methodology that already lives elsewhere. **Never** put always-on, mistake-preventing
rules here (environment/GPU pinning, commit policy, no fire-and-forget) — those belong in the
spine / `CLAUDE.md`; this file is the on-demand depth.

**B. Edit an existing note (medium friction).** Read the target in full, show the proposed diff
(or a tight before/after), and wait for approval before writing. A silent edit can change a
recipe, a default, or a number other reasoning depends on. Make the minimal change; do not
restructure unasked. Update the `**Summary:**` line only if the scope shifted.

**3. Refresh the index.** Run `/paper-index technical`.

**Always:** keep the index-to-leaf split (the index points and summarizes, the leaf holds the
depth); never invent numbers or paths, write "TBD" instead; if the knowledge looks paper-worthy,
suggest `/papernote`, never write `paper_narrative.md` here.
