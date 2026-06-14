# Redis key scheme

**Summary:** key naming scheme + TTLs

Pattern: `<entity>:<id>` (e.g. `cart:{user_id}`, `session:{token}`). All keys carry a TTL;
default 15 min for carts, 24h for sessions. No key is written without a TTL, to bound staleness
if an invalidation is ever missed.
