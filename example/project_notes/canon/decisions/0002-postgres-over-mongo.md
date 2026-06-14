# 0002 Postgres over Mongo

**Summary:** chose postgres for relational integrity

**Decision:** Postgres is the primary datastore.

**Rationale:** the domain is highly relational (users, carts, orders) and we want foreign-key
integrity plus transactions. Document flexibility was not worth giving those up.
