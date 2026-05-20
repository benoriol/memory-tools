<!-- memory-graph-mcp:protocol:start
     Managed by `memory-graph install-claude-md`. You can edit between
     these markers — the install command won't overwrite your edits
     unless you pass --force. To remove this section entirely, delete
     everything between (and including) the start/end markers. -->

## Memory protocol

This project has a persistent, per-project memory graph wired in via
the `memory-graph` MCP server. You have 13 `memory_*` tools available.

The three high-level ones to use day-to-day:

- **`memory_retrieve(query, intent="decide")`** — surface relevant past
  memories before acting. Cheap; the sub-agent does the walking and
  returns a focused synthesis with cited ids.
- **`memory_remember(dump)`** — write notes after work. Pass a thorough,
  free-form description (multi-paragraph is fine). The sub-agent
  decomposes it into the right notes at the right abstraction levels —
  you don't have to think about kinds or edges.
- **`memory_compact(scope?)`** — occasional cleanup pass over a region.
  Use rarely; only when memory feels noisy.

Plus ten primitives if you want direct control: `memory_search`,
`memory_get`, `memory_neighbors`, `memory_capture`, `memory_capture_batch`,
`memory_link`, `memory_unlink`, `memory_supersede`, `memory_mark`,
`memory_status`.

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

- A completed experiment — **successes AND failures both matter**
- A non-obvious design decision
- A surprising bug whose lesson generalizes
- Learning something that would change how you'd approach this next time

Pass a thorough dump. Include concrete handles (file paths, commit
hashes, metrics, hyperparameters) where relevant.

### Heuristic for "worth remembering"

> Would you tell a teammate about this lesson? Would you want to recall
> it six months from now?

If yes → `memory_remember`. If it's obvious from the code → don't.
Failed experiments are the highest-leverage notes; they save future-you
from retrying the same dead end.

<!-- memory-graph-mcp:protocol:end -->
