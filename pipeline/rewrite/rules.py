"""Rearrangement rules, written as CircIL rewrite patterns.

Each rule only reorders terms already present in the matched subtree, so
a circuit that typechecked before the match typechecks after it. No side
conditions: shape compatibility is inherited from the match succeeding.

Two things a pattern over these calls has to get right:

- The chevron list is the call's *template arguments*, the resolved
  values of the spec's `with_generic_value` parameters. A generated
  `matmul` carries three of them, so a pattern that omits them matches
  nothing. That is what `(matmul<?m, ?k, ?n> ...)` is.
- A call the rewrite side *builds* needs its result type spelled out,
  because the parser defaults an unannotated call to Field. Dimensions
  bound by the match are read back through `matrix<?rows, ?cols>`, the
  hint registered by `pipeline.matrix.MatrixHint`.
"""
from __future__ import annotations

import pipeline.circil as _circil_path_setup  # noqa: F401
from typing import Any

from circil.rewrite.rule import Rule  # type: ignore[import-not-found]

import pipeline.matrix as _matrix_hint_registration  # noqa: F401

# (a @ b)^T -> b^T @ a^T. With a: m x k and b: k x n, the product is m x n
# and its transpose n x m, which is what the rebuilt matmul must produce.
TRANSPOSE_OF_PRODUCT = Rule(
  "transpose-of-product",
  "(transpose<?m, ?n>:?t<matrix> (matmul<?m, ?k, ?n>:?u<matrix> ?a ?b))",
  "(matmul<?n, ?k, ?m>:?t"
  " (transpose<?k, ?n>:matrix<?n,?k> ?b)"
  " (transpose<?m, ?k>:matrix<?k,?m> ?a))",
)

# (a^T)^T -> a. The outer transpose's template arguments are the inner
# one's reversed, which is the whole side condition, and the match
# carries it.
DOUBLE_TRANSPOSE_ELIM = Rule(
  "double-transpose-elim",
  "(transpose<?x, ?y>:?t<matrix> (transpose<?y, ?x>:?u<matrix> ?a))",
  "?a",
)

ADD_COMMUTE = Rule(
  "add-commute",
  "(add<?m, ?n>:?t<matrix> ?a ?b)",
  "(add<?m, ?n>:?t ?b ?a)",
)

REARRANGEMENTS: tuple[Any, ...] = (
  TRANSPOSE_OF_PRODUCT,
  DOUBLE_TRANSPOSE_ELIM,
  ADD_COMMUTE,
)
