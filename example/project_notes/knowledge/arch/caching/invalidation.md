# Cache invalidation

**Summary:** when and how cache entries are dropped

Rule: any write path that mutates an entity MUST evict that entity's cache key in the same
transaction boundary. Read-through repopulates on the next read. The 2026-06-10 stale-cart bug
came from a remove path that skipped this step.

See journal/2026/06/2026-06-10-cache-bug-postmortem.md.
