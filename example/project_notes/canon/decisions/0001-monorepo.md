# 0001 Monorepo

**Summary:** why one repo for all services

**Decision:** all services live in one repository.

**Rationale:** atomic cross-service changes, one CI config, shared tooling. The cost (slower
clone, coarse permissions) is acceptable at current team size. Revisit past ~40 engineers.
