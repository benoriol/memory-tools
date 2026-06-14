# Request lifecycle

**Summary:** path of a request from edge to db

Edge (TLS, WAF) -> API gateway (authn, rate limit) -> service router -> handler -> cache check
-> Postgres. Responses are written back through the cache layer on read-through misses.

Timeouts: gateway 5s, handler 3s, db query 1s. A handler that exceeds its budget returns 503
rather than holding the connection.
