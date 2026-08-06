---
name: This is a fuzzer, not a verifier — sample, don't enumerate
description: Combinatorial blowup is the everyday workload of testing. Don't scope a design by "this would be too many configurations to enumerate."
type: feedback
originSessionId: bca48558-f79c-4fde-9eb1-14776414cc7e
---
In this project we **test** malicious-secure MPC protocols; we don't verify them. The methodology is sampling, not enumeration. Combinatorial growth in the search space (programs × operators × corrupt sets × seeds) is **the workload of a fuzzer**, not a constraint to design around.

**Why:** Early scoping documents (now-deleted `notes/fault-injection-design.md`) restricted the corrupt set to size 1 with the explicit reason "search space grows combinatorially." User pushed back hard: that's solver/verifier reasoning, not fuzzer reasoning. Carrying over the constraint-solver mindset by reflex is a recurring failure mode.

**How to apply:**
- When sizing scope, ask "is the sampling budget sufficient?" not "is this enumerable?"
- Bound by *time / runs / coverage*, not by *configuration count*.
- Don't pre-restrict parameters because their cross-product looks big. Sample over them.
- If a parameter has a meaningful bound from the *threat model* (e.g. `t < n/2` for honest-majority), that's a model constraint and stays. "Combinatorial blowup" alone is not a model constraint.
