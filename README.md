# memory-commands

A generic, reusable note-taking command set for Claude Code. A project-agnostic
generalization of an experiment-logging system: explicit control over what gets written
where and when, per-store gating, and a strict split between always-read context and
on-demand recall.

Ships in two **profiles**:
- **generic** (`/mem-*`): `journal/` · `knowledge/` · `canon/`. The default; good for any project.
- **paper** (`/logexp`, `/technote`, `/papernote`, `/note`, `/whattonote`, `/paper-audit`,
  `/paper-init`, `/paper-index`): a research variant where the journal becomes dated
  **experiments** with a paper-critical **important subset**, knowledge becomes **technical
  notes**, and canon becomes a paper-format **narrative**. See [Paper profile](#paper-profile).

## Install

Keep this folder as a git repo and `git pull` to get new versions of the commands; refresh them
into a project with `mem update`.

One-time, put the `mem` CLI on your PATH:

```
ln -s "$PWD/mem" ~/.local/bin/mem      # run from the module dir; ~/.local/bin must be on PATH
```

Then opt a project in, per project:

```
cd ~/code/some-project
mem install            # auto-detect the profile (generic vs paper), then confirm
mem install generic    # force the generic profile (/mem-*)
mem install paper      # force the paper profile (/logexp, /technote, ...)
mem install paper --link   # symlink instead of copy (central updates; see below)
                       # then, inside Claude Code: /mem-init (generic) or /paper-init (paper)
                       # to scaffold notes + wire the contract
mem update             # pull new versions of the commands from the module, keeping your edits
mem status             # show each command's state (copied / linked / modified)
mem uninstall          # remove this module's commands here (keeps copies you edited)
```

Bare `mem install` sniffs the project for research signals (`paper_writeups/`, `*.tex`, `wandb/`,
`checkpoints/`, an existing `project_notes/experiments*`) and suggests `paper`, otherwise
`generic`; it asks for one confirmation (and falls back to the guess when run non-interactively).

### Copy (default) vs `--link`

`mem install` **copies** the command files into the project's `.claude/commands/` by default, so
each project owns real files you can **customise for project-specific needs**. Refresh them later
with `mem update`: it re-copies commands that changed upstream but **skips any you edited locally**
(reporting them; `mem update --force` overwrites them). This is clone-friendly — the commands
travel with the repo for collaborators who do not have the module. A small `.mem-manifest` in
`.claude/commands/` records what was installed so update/uninstall can tell your edits from
upstream changes.

`mem install --link` **symlinks** into the module instead: one source of truth, so `git pull` in
the module updates every linked project at once, no `mem update` needed. The trade-offs: editing a
linked command edits the module (so it hits every project), and symlinks break when the project is
cloned without the module. Use `--link` for projects you never customise.

Either way, `install` never overwrites a real file it does not own, and `uninstall` removes only
this module's commands — keeping any copy you have edited (delete those by hand if you want them
gone). Switching profiles is `uninstall` then `install <other>`; override the target dir with
`CLAUDE_COMMANDS_DIR`.

## The three context tiers

- **Spine** (always read): a managed `## Memory` block inside the project `CLAUDE.md`. Rules,
  the read-first contract, and gating only. Tiny. The harness always loads `CLAUDE.md`, so this
  is genuinely always-on; there is no separate spine file to maintain or read. `/mem-init`
  writes and refreshes the block (only between its markers).
- **Indexes** (always read): one auto-generated index per store, a sibling file `<store>.md`
  (`journal.md`, `knowledge.md`, `canon.md`) holding the full tree plus a one-line summary per
  note. The only always-loaded view of deep memory.
- **Leaves** (recall, on demand): the detail notes, nested in the store folders, read only by
  following an index.

## The three stores

- `journal/` — dated run/event logs. Low gating. Chronological; "recent" is the tail.
- `knowledge/` — durable methods, facts, gotchas. Low to add, medium to edit. Topic tree.
- `canon/` — the curated project story, key decisions, rationale. High gating, sentence-level
  approval.

## Leaf format

Every note starts with a title and a one-line summary, then the details:

```
# <title>
**Summary:** <one line, copied verbatim into the index>

<full details>
```

The summary is the single source of truth for that note's index entry, so the index can be
regenerated from the notes and never drifts.

## Notes are fallible

The notes can be stale or wrong. They are used actively but never trusted over what can be
observed in the code, files, and results; verify when it matters. Anything off noticed while
working (a note that contradicts the code or another note, a number that no longer matches, a
dangling link, a stale "results pending") is raised to the user on the spot, with what and
where, not silently fixed. This is a continuous, surface-level check that fires whenever
something is encountered; `/mem-audit` is the deliberate, exhaustive version. The clause lives
in the `CLAUDE.md` memory block, so it is always-read context on every task.

## Notes root

Default `./project_notes/` in the current working directory. Override with the `MEM_ROOT`
environment variable, or pass a path to `/mem-init`.

## Commands

Setup and indexing:
- `/mem-init [path] [sources...]` — scaffold the notes root, wire the contract into `CLAUDE.md`,
  build a context model for the project, and optionally migrate existing notes into the
  structure (proposal-first, non-destructive). Idempotent.
- `/mem-index [store]` — rebuild the full-tree index from disk; run after any write.

Writers (each refreshes its index when done):
- `/mem-log` — journal: a dated event or result. Low gating.
- `/mem-note` — knowledge: durable method, fact, or gotcha. Low to add, medium to edit.
- `/mem-canon` — canon: project story, decisions, rationale. High gating, line-by-line approval.

Routing and review:
- `/mem` — router: classify a capture, confirm the route, delegate to a writer.
- `/mem-audit` — read-only consistency sweep across the stores; proposes fixes, never silent.
- `/mem-suggest` — read-only "what is worth capturing here?" advisory.

## Gating summary

| Store | Add | Edit | Notes |
|---|---|---|---|
| `journal/` | low | n/a (append-only) | never overwrite a leaf |
| `knowledge/` | low | medium (diff shown) | new subfolder = confirm first |
| `canon/` | high | high | sentence-by-sentence approval, advise-first |

## Paper profile

A research-oriented variant of the same system (same tiers, same gating philosophy, same
single-source-of-truth indexes), shipped under `profiles/paper/`. Install it with
`mem install paper`; scaffold a project with `/paper-init`. A runnable example tree lives in
`profiles/paper/example/`.

What changes versus the generic profile:

| generic | paper | difference |
|---|---|---|
| `journal/` + `journal.md` | `experiments/` + `experiments.md` | dated run leaves; richer fields (Why / Headline / Important / Type / Setup / Result / Paths) |
| — | `experiments_important.md` | **new always-read tier**: the paper-critical subset |
| `knowledge/` | `technical_notes/` | durable methodology / gotchas (same protocol) |
| `canon/` | `paper_narrative.md` | one curated doc, laid out in paper order (abstract → method → results → ablations → supplementary → open) |
| `/mem-log` `/mem-note` `/mem-canon` | `/logexp` `/technote` `/papernote` | writers |
| `/mem` `/mem-suggest` `/mem-audit` | `/note` `/whattonote` `/paper-audit` | router / advisory / audit |
| `/mem-init` `/mem-index` | `/paper-init` `/paper-index` | scaffold / rebuild indexes |

**The important subset is a projection, not a second list.** Each experiment leaf carries an
`**Important:** yes|no` flag; `/paper-index` rebuilds both `experiments.md` (all runs) and
`experiments_important.md` (only the flagged ones) from the leaves. To promote or demote a run you
flip the flag on its leaf and rerun the index, never hand-edit the subset, so it can never drift.

The paper profile uses a **flat layout** (one research line per project). The
`image_control` project keeps its own bespoke multi-line (`project_notes/<line>/`) setup; that
generalization is intentionally out of scope here.

### Paper gating summary

| Destination | Add | Edit | Notes |
|---|---|---|---|
| `experiments/` + `experiments.md` | low | n/a (append-only) | never overwrite a leaf |
| `experiments_important.md` | medium (explicit ask sets the flag) | via the leaf flag | rebuilt by `/paper-index`, never hand-edited |
| `technical_notes/` | low | medium (diff shown) | |
| `paper_narrative.md` | high | high | sentence-by-sentence approval, advise-first |
