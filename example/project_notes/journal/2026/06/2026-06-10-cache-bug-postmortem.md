# 2026-06-10 Stale cart cache postmortem

**Summary:** stale cart cache root-caused to a missing invalidation on item removal

**Why:** users reported removed items reappearing in their cart.

**Root cause:** the remove-item path updated the DB but never evicted the Redis cart key, so
reads served the stale cached cart until TTL expiry (15 min).

**Fix:** evict `cart:{user_id}` in the remove path; added a regression test.

**Cross-references:** knowledge/arch/caching/invalidation.md, knowledge/arch/caching/redis-keys.md
