---
name: mpspdz-jump-model
description: "MP-SPDZ jumps (`jmp`, `jmpi`, `jmpnz`, `jmpeqz`) are all over public state. No secret-conditioned jump exists. Every party traverses identical control-flow paths. So static sync-op sequence == dynamic sync-op sequence on every party."
metadata: 
  node_type: memory
  type: project
  originSessionId: f2a091fa-b56a-4655-90bc-5449ebb07127
---

**Fact.** Every MP-SPDZ jump opcode reads only public state:

- `jmp`: compile-time `int` offset, unconditional.
- `jmpi`: `ci` register (clear integer = public).
- `jmpnz`, `jmpeqz`: condition is a `ci` register.

Secret-conditioned branching does not exist in MP-SPDZ bytecode.
Source-level secret conditionals (e.g. `(condition).if_else(a, b)`) are
compiled to MUX — straight-line oblivious selection, no actual branch.

**Why this matters for fault-injection checks.** Since all parties see
the same public state and run the same bytecode, every party traverses
the same path through every jump. The dynamic sync sequence equals the
static sync sequence on every party.

So when checking that a mutation preserves the inter-party sync
invariant, you only need to compare the *static* `DataInstruction`
sequence on each tape (helper: `sync_signature` in
`pipeline/mpspdz.py`). No need to model control-flow shape; equivalent
control flows can't end up running different paths in this protocol.

**How to apply.** When designing sync-preservation checks, audit the
opcodes the mutation can produce. If it can only emit local arithmetic
that doesn't touch `DataInstruction` subclasses, the check passes by
construction. If it might emit new OPENs / triples / inputmasks, the
check is meaningful.

**Where this stops applying.** If a future gadget class steps outside
the bytecode (skip-CHECK, direct C++ patching, runtime corruption of
the `ci` register feeding a jump), then per-party control-flow
divergence becomes possible and a richer invariant is needed. The
BLUEPRINT puts these out of scope for now.
