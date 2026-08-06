---
name: keep-adapter-layer-pokes-out-of-business-logic
description: "Low-level MP-SPDZ accesses (inst.args[0], type(inst).__name__, addsi(..., add_to_prog=False), …) belong in adapter helpers, not in the middle of gadget/component logic. The helpers can stay messy; the call sites must read cleanly."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cb94fbd6-51fc-4916-b29c-aecbc9c30155
---

**Rule.** Don't write `inst.args[0]`, `type(inst).__name__ == "ldsi"`, raw `add_to_prog=False` instruction construction, or other MP-SPDZ-internal pokes inline in a business-logic method (gadget `apply`, an oracle classifier, etc.). Extract them into small helpers (free functions or thin wrappers) in an adapter module — `pipeline/mpspdz.py` or similar.

**Why:** the call sites are doing one job (the gadget's transform, the oracle's classification, ...). Inlining the adapter's idiosyncrasies obscures that. The adapter helpers themselves can stay ugly — that's the price of working with MP-SPDZ's API — but the *consumers* must read cleanly. Otherwise every reader has to understand both the business logic AND the MP-SPDZ internals at once.

**How to apply:**
- When a method on a component reaches into `inst.args`, `type(inst).__name__`, `program.tapes[i].basicblocks[0]`, or constructs an `Instruction` via the auto-append API, that's a smell.
- Move the poke into an adapter helper (e.g. `find_first(tape, opcode)`, `make_addsi(...)`, `insert_after(...)`).
- Give the helper a name that describes intent, not mechanism.
- If you find yourself wondering whether to factor it out: do it. The bar is "the logic reads cleanly without knowing MP-SPDZ's API."
