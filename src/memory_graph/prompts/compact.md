# Task: compact

You're consolidating part of the graph. The main agent has either
named a scope (`cluster:X`, `topic:Y`, or `recent`) or asked for a
general pass.

## Workflow

1. **Pick a region.** If a scope was given, use it. Otherwise look at
   `status()` and the operator-context for the densest / dirtiest
   region (high node count, recent activity, status:unsure or
   status:disputed concentration).

2. **Walk the region.** Use `search` and `neighbors` to enumerate the
   notes. Read their summaries.

3. **Spot opportunities.** For each:
   - **Duplicate**: cosine ~1.0 with shared meaning → `supersede` the
     weaker / older one
   - **Cluster without a hub**: ≥5 cohesive notes on one topic without
     a parent → propose creating a hub note (capture_batch with the
     hub + `generalizes` edges from members)
   - **Drifted concept**: notes that share vocabulary but mean
     different things → leave with a note in your response
   - **Stale stative**: `reference` notes with old `last_verified_at`
     → call `mark(id, "stale")` if the underlying code has clearly
     changed (you can ask `Read` if you have it; otherwise flag)
   - **Disproven**: notes contradicted by newer evidence → mark or
     supersede

4. **Apply changes.** Make the writes / marks / supersedes. Don't
   delete; the graph keeps history.

5. **Respond.** Return:
   - `region`: what you operated on
   - `changes`: list of {action, ids, reason}
   - `notes`: prose summary of what shape the region is in now and what
     a future pass should look at
