# 2026-06-08 OAuth login rollout

**Summary:** shipped oauth login to 100% of users

**Why:** replace the legacy password form with the new OAuth flow.

**What happened:** staged 10% -> 50% -> 100% over the day. Error rate stayed flat at 0.2%.
Median login latency dropped from 740ms to 410ms.

**Paths:** feature flag `auth.oauth_only`, dashboard `grafana/auth-rollout`.

**Follow-up:** delete the legacy form code once the flag bakes for a week.
