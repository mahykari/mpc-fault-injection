---
name: feedback-walker-for-tree-traversal
description: "When traversing tree-structured IRs (CircIL AST, future similar substrates), use the library's visitor/walker pattern (subclass EmptyVisitor / IRWalker) rather than a single recursive function dispatching on isinstance."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f2a091fa-b56a-4655-90bc-5449ebb07127
---

For tree-structured IRs that ship a visitor base class (e.g. CircIL's
`EmptyVisitor` / `IRWalker` in `circil/ir/visitor.py`), translation /
analysis code should **subclass the walker and override `visit_*`
methods**, not flatten it into a single recursive function with
`isinstance` chains.

**Why:** the library's walker already encodes the dispatch table, the
recursive structure, and the per-node-type method names. Reimplementing
that as a flat function reads as "I don't trust the library" and
duplicates structure. The walker pattern is also how new node types
are added cleanly later — override one more `visit_*` method.

**How to apply:** when consuming a library that provides a visitor
base, follow its pattern. For expression-text accumulation during
traversal, hold a buffer (e.g. `self._expr: list[str]`) on the walker
instance and have leaf visitors `append` to it; the composing visitor
(call/ternary/etc.) wraps with brackets and operators between child
visits. See `pipeline/translator.py:MpspdzTranslation` for the
canonical example in this repo.
