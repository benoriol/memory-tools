# On-call gotchas

**Summary:** recurring incidents and their fixes

- Connection pool exhaustion under retry storms: cap client retries at 3 with backoff.
- Disk fills from unrotated debug logs: logrotate runs at 80% via the `disk-guard` cron.
- Redis failover drops the read replica for ~5s: clients must retry transient connection errors.
