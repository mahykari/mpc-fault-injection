---
name: feedback_dont_verify_invariants
description: "On PR/code review, don't run mypy or main.py to \"verify\" the load-bearing invariants"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a26058fb-6cc7-452a-8afa-8b21c7479a2f
---

When reviewing a PR or change, don't burn a turn running `uv run mypy` or `uv run python main.py` to confirm the BLUEPRINT invariants hold — the user already knows they pass.

**Why:** It's wasted verification; the user keeps those green as a matter of course.
**How to apply:** Review from the diff. Reserve actually running things for when behavior is genuinely in question, not the standing invariants. Relates to [[feedback_terse_no_commentary]].
