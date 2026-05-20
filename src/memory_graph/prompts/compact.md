# Task: compact

Consolidate part of the graph. The caller has either named a `scope`
(e.g. `cluster:X`, `topic:Y`, `recent`) or asked for a general pass.

## Workflow

1. **Pick a region.** If a scope was given, use it. Otherwise consult
   `status()` and the operator-context for the densest or dirtiest
   region — recent activity, many `unsure` / `disputed` nodes, high
   embedding density without abstraction structure.

2. **Walk the region.** Enumerate the notes with `search` +
   `neighbors`. Read their summaries.

3. **Spot opportunities.**

   - **Duplicates** (high cosine, same meaning): keep one, `supersede`
     the others.
   - **Missing abstraction structure**: when several notes describe
     the same recurring pattern but no abstracting note exists,
     write one with `kind: principle` (or another descriptive label)
     and draw `abstracts` edges from it to the concrete members.
   - **Drift**: notes that share vocabulary but mean different things
     — flag in your response.
   - **Stale**: notes referencing code that's changed. Mark with
     `mark(id, "stale")` so retrieval down-weights them.
   - **Disproven**: notes contradicted by newer evidence — `supersede`
     or `mark` accordingly.

4. **Apply changes.** Make the writes / marks / supersedes. Don't
   delete; the graph keeps history.

5. **Respect `user_said`.** Never auto-supersede a `user_said` note
   without flagging in `clarifications_needed`. User directives stay
   unless the user retracts them.

## Response shape

- `region`: what you operated on
- `changes`: list of `{action, ids, reason}`
- `notes`: prose summary of the region's shape and what a future pass
  should look at next
