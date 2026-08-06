---
name: feedback-stay-high-level
description: "Approach this as a fuzzer user, not an MPC theorist. Don't dig into protocol internals to justify or fix injector behavior — try things, observe outputs, discard inert cases."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 636bf176-9417-477c-acc6-97c76330ccfc
---

Operate at the fuzzer-user level: generate program → inject → run → look at output. If the mutated output differs from honest, the program is useful. If not, scrap it and regenerate. Do not reason about *why* a particular gadget did or didn't propagate through MAC shares, value shares, dead registers, etc.

**Why:** user 2026-05-26 — "the thing we're digging here is more of our own grave rather than a good solution: let's stay high-level, try things as someone who doesn't have to understand all the subtle tricks of MPC, and just wants to test this system." Digging into asymmetric sharing, def-use analysis, etc. is the wrong layer.

**How to apply:**
- Don't propose protocol-internals fixes (symmetric-bump gadgets, live-path analysis, anchor targeting heuristics) as solutions to "mutation didn't show up."
- Inert mutations are not a bug to investigate — they're noise to filter.
- Notes documenting MPC subtleties are fine as reference, but don't make them load-bearing for the design.
- See also [[feedback_testing_not_verifying]] (sample-don't-enumerate is the same instinct).
