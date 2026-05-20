<!-- memory-graph-mcp:protocol:start
     Managed by `memory-graph install-claude-md`. You can edit between
     these markers — the install command won't overwrite your edits
     unless you pass --force. To remove this section entirely, delete
     everything between (and including) the start/end markers. -->

## Memory protocol

This project has a persistent, per-project memory graph wired in via
the `memory-graph` MCP server. The model is deliberately flat: every
note is the same kind of thing, with a free-text `kind` label for
description and three edge types — `abstracts`, `related`,
`supersedes` — that's it.

Three high-level tools to use day-to-day:

- **`memory_retrieve(query, intent="decide|explore|verify")`** —
  surface relevant past memories before acting. Cheap; the sub-agent
  walks the graph (both upward toward abstract context and downward
  toward concrete evidence) and returns a focused synthesis with
  cited ids.
- **`memory_remember(dump)`** — write notes after work. Pass a
  thorough, free-form description (multi-paragraph is fine). The
  sub-agent slices it into one or more notes, picks `kind` labels,
  and connects them with `abstracts` / `related` edges as appropriate.
- **`memory_compact(scope?)`** — occasional cleanup pass over a
  region. Use rarely; only when memory feels noisy.

Plus primitives (`memory_search`, `memory_get`, `memory_neighbors`,
`memory_capture`, `memory_capture_batch`, `memory_link`,
`memory_unlink`, `memory_supersede`, `memory_mark`, `memory_status`)
for direct control.

### When to call `memory_retrieve`

Strongly encouraged before:

- Designing an experiment or picking an approach
- Making a non-trivial decision (architectural, design, scoping)
- Modifying load-bearing code (customize this list per project)
- Starting a fresh session — to refresh context on what's been tried

Cite returned ids inline in your reasoning. If a returned note
contradicts what you're about to do, address it explicitly: either
argue why the prior finding no longer applies, or change course.

### When to call `memory_remember`

Strongly encouraged after:

- Completing an experiment — **successes AND failures both matter**
- Making a non-obvious design decision
- Hitting a surprising bug whose lesson generalizes
- Learning something that would change how you'd approach this next time
- The user shares substantive context (vision, constraint,
  preference, plan) — capture these as `kind: user_said`

Pass a thorough dump. Include concrete handles (file paths, commit
hashes, metrics, hyperparameters) where relevant.

### How `user_said` notes are weighted

`user_said` notes get **priority attention** at retrieval — they're
context the agent should foreground. But they are not unconditional
truth: a user can change their mind, a remark may have been a working
assumption, a plan can go stale. Treat them like a strong prior
that's still subject to the normal lifecycle (`supersedes`,
`status: stale`).

### Heuristic for "worth remembering"

> Would you tell a teammate about this lesson? Would you want to
> recall it six months from now?

If yes → `memory_remember`. If it's obvious from the code → don't.
Failed experiments and `user_said` notes tend to be the
highest-leverage entries — failed experiments save future-you from
retrying dead ends, and `user_said` notes carry intent that's
expensive to re-elicit.

<!-- memory-graph-mcp:protocol:end -->
