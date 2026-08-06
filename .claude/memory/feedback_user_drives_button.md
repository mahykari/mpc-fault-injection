---
name: feedback_user_drives_button
description: "User runs consequential/ownership actions themselves — launching campaigns, pushing, closing PRs; prep and hand off, don't run them"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a26058fb-6cc7-452a-8afa-8b21c7479a2f
---

The user wants hands on the consequential/ownership steps: starting a fuzz campaign ("I want to push the red button"), pushing branches, closing PRs, building images on their server. Prep them to a single command and hand it over; don't run them, and don't keep re-offering after they decline.

**Why:** They stay sharp by driving the load-bearing actions themselves — "asking a runner to just watch the treadmill, there'll be atrophies." Doing it for them erodes that.
**How to apply:** Reversible setup that follows from the request (commits, rsync, config edits, read-only checks) — just do it. Launches/pushes/deploys — give the exact command and stop. One offer max, then drop it. Relates to [[feedback_suggest_dont_write]] and [[feedback_dont_escalate_small_asks]].
