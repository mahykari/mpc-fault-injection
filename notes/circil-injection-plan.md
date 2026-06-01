# CircIL-level injection plan

Move the Injector from MP-SPDZ IR to the CircIL AST.

- Anchor = any `Assignment` statement. Wrap its `rhs`:
  - Bump: `rhs ← CallExpression(ADD, [rhs, Integer(±1)])`
  - SignFlip: `rhs ← CallExpression(MUL, [rhs, Integer(-1)])`
- Pipeline: generate → inject (CircIL) → translate ×2 → compile ×2 → execute.
- Drop IR-mutation helpers in `pipeline/mpspdz.py`; keep `sync_signature` for the post-compile invariant check.
- Diff becomes a DSL diff (legible) instead of an opcode diff.
