---
name: feedback_simple_commands
description: "No opaque multi-step bash. Run ONE dead-simple command at a time, or plainly say what a command does before running it."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: db3d86a0-5d48-40b3-8aa5-55b9590cdbf6
---

User: "i'm tired of these wizard-ass commands that you run. you've either gotta tell me what you're trying to run, or you've gotta run dead-ass simple things."

**Do NOT** run long compound bash in one shot — chained `&&`/`;` steps, `ssh ... 'bash -s' < script`, nested greps, pkill self-match traps, multi-target one-liners. The user can't follow or trust them on their infra.

**Instead, pick one:**
1. Run **one dead-simple command** at a time (e.g. `ssh host pgrep -af continuous.py`), see the result, then the next.
2. Or, before running anything non-trivial, **say in plain words what the command does** and why.

Prefer simple-and-explained. One step, show the output, decide the next step together. This pairs with [[feedback_be_decisive]] (less deliberation) and [[feedback_user_drives_button]] — but the point here is transparency and simplicity of the *commands themselves*, not just the prose.
