# Task: retrieve

The main agent has described something it's working on or about to
decide. Surface relevant memories with citations.

## Workflow

1. **Expand the query.** Generate 4–8 alternate framings or related
   concerns. The query may be narrow; the user might be touching
   adjacent concerns without naming them. Use the operator-context to
   spot non-obvious couplings.

2. **Search broadly.** Run `search` for each framing; union the
   candidates.

3. **For every promising hit, walk both directions.** This is the
   default — do it regardless of the caller's `intent`:

   - **Upward** (1–2 hops on **incoming** `abstracts`): the more
     abstract context that frames the hit. A specific experiment
     surfaces the principle that informs it; a `user_said` constraint
     surfaces the goal it serves.
   - **Downward** (1 hop on **outgoing** `abstracts`, if the seed is
     itself abstract): the concrete evidence behind the rule. A
     `principle` surfaces the experiments / observations that
     justify it.
   - **Lateral** (1 hop on `related`): adjacent context.

4. **Bias toward `user_said` notes.** If a `user_said` note is in
   range, include it in the synthesis — these are directives, not
   observations. Never silently set aside a `user_said` constraint.

5. **Handle conflicts and supersession.** If a hit has been
   `superseded` by something else, follow the supersedes edge and
   include the *newer* note. Mention the supersession in the synthesis
   so the agent knows the prior version was retired and why.

6. **Cap and synthesize.** Limit the expanded set to ~6 nodes per
   seed before reranking. Filter to what's actually relevant to the
   stated intent. Then write a tight prose synthesis with `[id]`
   citations inline.

## Intent (soft hint)

The caller passes `intent`:

- `decide` — the agent is about to make a choice. Prioritize
  principles, `user_said` constraints, decisions, and supersessions.
- `explore` — broad surface. Wider lateral walk on `related`.
- `verify` — checking a specific claim. Emphasize the upward walk
  (what abstracts this) and any contradictions or supersessions.

`intent` shapes *what to emphasize*, not which edges exist — there are
only three edge types and you walk them all.

## Response shape

Return:

- `synthesis`: 2–6 short paragraphs of focused prose with `[id]`
  citations inline.
- `cited`: list of `{id, kind, summary}` for every id you cited.
- `also_relevant`: list of `{id, why}` the agent might want next.
- `caveats`: contradictions, stale notes, `user_said` constraints, or
  coupling concerns the agent should know about.

Keep it tight. The main agent sees only your final response; the
exploration tokens stay here.
