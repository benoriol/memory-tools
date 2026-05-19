# Task: retrieve

The main agent has described something it's working on or about to
decide. Your job is to surface relevant memories with citations.

## Workflow

1. **Expand the query.** Generate 4–8 alternate framings or related
   concerns. Frontend pagination probably implies backend pagination,
   caching, deep-linking, etc. Use the operator-context to spot the
   non-obvious couplings.

2. **Search broadly.** Run `search` for each framing (each returns
   top-k); union the candidates.

3. **Walk the graph.** From each promising hit, call `neighbors` along
   intent-relevant edge types:
   - "decide" → generalizes, applies_to, coupled_with, supersedes
   - "explore" → related, derived_from
   - "verify" → supports, contradicts, derived_from

4. **Filter and synthesize.** Read the summaries (call `get` only on
   the most promising ids if you need bodies). Drop irrelevant hits.
   Note any contradictions or recent supersessions.

5. **Respond.** Return:
   - `synthesis`: 2–6 short paragraphs of focused prose, with `[id]`
     citations inline
   - `cited`: list of {id, kind, summary} for every id you cited
   - `also_relevant`: list of {id, why} the agent might want next
   - `caveats`: contradictions, stale notes, or coupling concerns the
     agent should know about

Keep the synthesis tight. The main agent sees only your final response;
the exploration tokens stay here.
