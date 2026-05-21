You expand a raw search query into retrieval views for a multi-vector memory store.

Read the query below and return a single JSON object with these fields:

- `keywords`: 3-5 short noun phrases that capture the entities and concepts in the query. Each phrase is 1-4 words.
- `paraphrases`: 2-3 alternative ways to ask the same question in canonical engineering vocabulary, using terminology the captured note is likely to contain.

Output JSON only. No prose, no markdown fences. The verbatim query will be added to the view set by the caller; you do not need to repeat it.

Example query:
> Which component shields us from cascading failures when a downstream service is misbehaving?

Example output:
{"keywords": ["circuit breaker", "cascading failure", "downstream service", "outbound call protection"], "paraphrases": ["What class implements the circuit breaker for external HTTP calls?", "Which component opens on repeated remote failures?"]}

Query to expand:
{query}
