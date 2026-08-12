"""Matrix custom type and its CircIL function table.

CircIL has no shape-polymorphic templates for `Custom` types, so the
shape is folded into the type *name* and every concrete shape triple
gets its own `FunctionSpecification`. The fuzzer then picks operands
by return type and the shapes line up for free.
"""
from __future__ import annotations

import pipeline.circil as _circil_path_setup  # noqa: F401
from itertools import product
from random import Random
from typing import Any

import circil.ir.types as IRType  # type: ignore[import-not-found]
from circil.ir.functions import FunctionSpecification  # type: ignore[import-not-found]

DIMS: tuple[int, ...] = (2, 3)
SHAPES: tuple[tuple[int, int], ...] = tuple(product(DIMS, DIMS))

MATMUL = "matmul"
MADD = "madd"
TRANSPOSE = "transpose"
FILL = "matrix_fill"


class Matrix(IRType.Custom):  # type: ignore[misc]
  """A fixed-shape matrix of field elements.

  The shape lives in `Custom.name`: `_storage_key`, `__hash__` and the
  fuzzer's type caches all key on the name, so carrying the shape only
  as an attribute would collapse every shape into one cache bucket and
  hand back mismatched operands with no error.
  """
  rows: int
  cols: int

  def __init__(self, rows: int, cols: int) -> None:
    super().__init__("Matrix[%dx%d]" % (rows, cols))
    self.rows = rows
    self.cols = cols

  def constructor(self) -> Any:
    return (
      FunctionSpecification(FILL)
      .takes("v", IRType.Field())
      .returns("m", Matrix(self.rows, self.cols))
    )

  @staticmethod
  def union_instances() -> tuple[Any, ...]:
    return tuple(Matrix(rows, cols) for rows, cols in SHAPES)

  @staticmethod
  def random_instance(rng: Random) -> Any:
    rows, cols = rng.choice(SHAPES)
    return Matrix(rows, cols)

  def __str__(self) -> str:
    return "Matrix[%dx%d]" % (self.rows, self.cols)

  def __repr__(self) -> str:
    return "Matrix(%d, %d)" % (self.rows, self.cols)


def matrix_specs() -> list[Any]:
  """One concrete spec per shape triple. Names repeat across shapes on
  purpose: lookup is by return type, so a rule matching `matmul` matches
  every shape."""
  specs: list[Any] = []
  for rows, inner, cols in product(DIMS, DIMS, DIMS):
    specs.append(
      FunctionSpecification(MATMUL)
      .takes("a", Matrix(rows, inner))
      .takes("b", Matrix(inner, cols))
      .returns("c", Matrix(rows, cols))
    )
  for rows, cols in SHAPES:
    specs.append(
      FunctionSpecification(MADD)
      .takes("a", Matrix(rows, cols))
      .takes("b", Matrix(rows, cols))
      .returns("c", Matrix(rows, cols))
    )
  for rows, cols in SHAPES:
    specs.append(
      FunctionSpecification(TRANSPOSE)
      .takes("a", Matrix(rows, cols))
      .returns("c", Matrix(cols, rows))
    )
  return specs
