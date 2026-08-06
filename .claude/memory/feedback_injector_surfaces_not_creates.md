---
name: feedback_injector_surfaces_not_creates
description: The injector surfaces existing MP-SPDZ bugs; it never creates/changes them. Frame reachability accordingly.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0e5d5f98-876f-42bd-a721-faa66a6f6eeb
---

The testing pipeline never modifies MP-SPDZ. It injects a deviation (wrong value on corrupt parties); a missing/weak check is an *existing* bug. If the injected deviation rides through that unchecked path → silent wrong output = we *surfaced* the bug. If the check is correct, it catches the deviation and aborts.

**Why:** I framed "reachability" as "can our mutation create the skip-check condition" (e.g. "we can't turn off a check") — wrong. We never create or disable anything.

**How to apply:** Ask "can our injected deviation reach the path where the check is already missing?" not "can we disable a check?". Races stay unsurfaceable (single-threaded can't make the interleaving); most skip-checks unsurfaceable because the gap is in preprocessing/OT/threading our register-level deviation never reaches; the truncation `reveal(check=False)` case is surfaceable in principle since a perturbed value can flow through it. See [[project_mpspdz_jump_model]].
