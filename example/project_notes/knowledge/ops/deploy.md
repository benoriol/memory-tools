# Deploys

**Summary:** blue/green deploy steps + rollback

Blue/green: deploy to the idle color, run smoke tests, flip the load balancer. Rollback is a
flip back to the previous color, which stays warm for 1 hour post-deploy. Never deploy both
colors at once.
