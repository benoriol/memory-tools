You expand a raw note into retrieval views for a multi-vector memory store.

Read the note below and return a single JSON object with these fields:

- `title`: 3-8 word descriptive title (string).
- `summary`: one declarative sentence stating the note's core fact.
- `keywords`: 3-5 short noun phrases someone might search for. Each phrase is 1-4 words. Cover the entities, the action, and any concrete identifiers.
- `paraphrases`: 2-3 different ways someone might ask a question this note would answer, in canonical engineering vocabulary. Full questions, not fragments.
- `tags`: 0-3 short topical tags (lowercase, hyphen-separated).

Output JSON only. No prose, no markdown fences.

Example input:
> The OutboundBreaker class wraps every external HTTP call and opens after five consecutive failures.

Example output:
{"title": "OutboundBreaker external-call circuit breaker", "summary": "OutboundBreaker is the circuit breaker wrapping all outbound HTTP calls; it opens after five consecutive failures.", "keywords": ["OutboundBreaker", "circuit breaker", "external HTTP failures", "five consecutive failures"], "paraphrases": ["Which class shields us from cascading failures when a downstream service is misbehaving?", "What is the circuit-breaker threshold for outbound calls?", "Which component trips on repeated remote errors?"], "tags": ["reliability", "networking"]}

Note to expand:
{content}
