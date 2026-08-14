"""Matrix custom type and its CircIL function table.

The shape lives in two value parameters resolved by CircIL's template
machinery, mirroring `circil.extensions.types.sized_string`: `matmul`
declares `m`, `k`, `n`, takes `Matrix<m,k>` and `Matrix<k,n>` and returns
`Matrix<m,n>`, and the constraint solver picks concrete dimensions per
call site.
"""
from __future__ import annotations

import pipeline.circil as _circil_path_setup  # noqa: F401
from functools import cached_property
from random import Random
from typing import Any, Callable, Optional

import circil.ir.types as IRType  # type: ignore[import-not-found]
from circil.ir.constraints import RangeConstraint  # type: ignore[import-not-found]
from circil.ir.functions import FunctionSpecification  # type: ignore[import-not-found]
from circil.ir.templates import TemplateType, TypeResolver  # type: ignore[import-not-found]
from circil.utils import intersection, value_inclusion  # type: ignore[import-not-found]

# Dimensions stay small: every generated circuit becomes an MP-SPDZ program,
# and a matmul is O(m*k*n) secret multiplications.
MIN_DIM = 1
MAX_DIM = 4

MATMUL = "matmul"
ADD = "add"
TRANSPOSE = "transpose"
FILL = "matrix_fill"

Dim = Optional[int]
DimArg = "int | range | None"


def _dim_equiv(left: Dim, right: Dim) -> bool:
  return left is None or right is None or left == right


class Matrix(IRType.Custom):  # type: ignore[misc]
  """A matrix of field elements with an optionally-unspecified shape.

  `rows`/`cols` of `None` match any dimension, the way an `Array` with
  size `None` does.
  """
  terminal = True

  rows: Dim
  cols: Dim

  def __init__(self, rows: Dim, cols: Dim) -> None:
    super().__init__("matrix")
    assert rows is None or MIN_DIM <= rows <= MAX_DIM, "rows out of range"
    assert cols is None or MIN_DIM <= cols <= MAX_DIM, "cols out of range"
    self.rows = rows
    self.cols = cols

  def equiv(self, other: Any) -> bool:
    if isinstance(other, _RequestMatrix):
      return bool(other.equiv(self))
    if isinstance(other, Matrix):
      return _dim_equiv(self.rows, other.rows) and _dim_equiv(self.cols, other.cols)
    return bool(self._generic_union_equivalence(other))

  @staticmethod
  def constructor() -> Any:
    return (
      FunctionSpecification(FILL)
      .with_generic_value("rows", IRType.Field())
      .with_generic_value("cols", IRType.Field())
      .takes("v", IRType.Field())
      .returns("m", MatrixTemplate("rows", "cols"))
      .constrained_by(RangeConstraint("rows", MIN_DIM, MAX_DIM))
      .constrained_by(RangeConstraint("cols", MIN_DIM, MAX_DIM))
    )

  @staticmethod
  def random_instance(
    rng: Random, nesting_level: int, random_type: Callable[[int], Any]
  ) -> "Matrix":
    return Matrix(rng.randint(MIN_DIM, MAX_DIM), rng.randint(MIN_DIM, MAX_DIM))

  @staticmethod
  def union_instances() -> tuple[Any, ...]:
    return (Matrix(None, None),)

  def undetermined_type_select(
    self, rng: Random, undetermined_type_select: Callable[[Any], Any]
  ) -> Any:
    rows = self.rows if self.rows is not None else rng.randint(MIN_DIM, MAX_DIM)
    cols = self.cols if self.cols is not None else rng.randint(MIN_DIM, MAX_DIM)
    return Matrix(rows, cols)

  @cached_property
  def is_generic(self) -> bool:
    return self.rows is None or self.cols is None

  def __str__(self) -> str:
    return "mat[%sx%s]" % (
      "@" if self.rows is None else self.rows,
      "@" if self.cols is None else self.cols,
    )

  def __repr__(self) -> str:
    return str(self)

  def __eq__(self, other: Any) -> bool:
    if not isinstance(other, Matrix):
      return False
    return self.rows == other.rows and self.cols == other.cols

  def __hash__(self) -> int:
    return hash((self.__class__, self.rows, self.cols))

  def canonical_key(self) -> Any:
    return (
      "custom", "matrix",
      -1 if self.rows is None else self.rows,
      -1 if self.cols is None else self.cols,
    )


class _RequestMatrix(Matrix):
  """A Matrix whose dimensions are still ranges rather than values.

  The solver hands back a `range` when a value parameter is not pinned
  yet; this carries it until `undetermined_type_select` collapses it.
  """
  _rows: Any
  _cols: Any

  def __init__(self, rows: Any, cols: Any) -> None:
    super().__init__(None, None)
    self._rows = rows
    self._cols = cols

  @staticmethod
  def _includes(mine: Any, theirs: Any) -> bool:
    if isinstance(mine, range):
      return bool(value_inclusion(mine, theirs))
    return _dim_equiv(mine, theirs)

  def equiv(self, other: Any) -> bool:
    if isinstance(other, Matrix):
      other_rows = other._rows if isinstance(other, _RequestMatrix) else other.rows
      other_cols = other._cols if isinstance(other, _RequestMatrix) else other.cols
      return self._includes(self._rows, other_rows) and self._includes(self._cols, other_cols)
    return bool(self._generic_union_equivalence(other))

  @cached_property
  def is_generic(self) -> bool:
    return True

  def undetermined_type_select(
    self, rng: Random, undetermined_type_select: Callable[[Any], Any]
  ) -> Any:
    return Matrix(_collapse(self._rows, rng), _collapse(self._cols, rng))

  def __eq__(self, other: Any) -> bool:
    if not isinstance(other, _RequestMatrix):
      return False
    return bool(self._rows == other._rows and self._cols == other._cols)

  def __hash__(self) -> int:
    return hash((self.__class__, str(self._rows), str(self._cols)))

  def __str__(self) -> str:
    return "mat[%s x %s]" % (self._rows, self._cols)


def _collapse(dim: Any, rng: Random) -> int:
  if isinstance(dim, range):
    return rng.randint(dim.start, dim.stop - 1)
  if dim is None:
    return rng.randint(MIN_DIM, MAX_DIM)
  return int(dim)


class MatrixTemplate(TemplateType):  # type: ignore[misc]
  """`Matrix<rows, cols>` with each dimension a literal or a value-parameter name."""

  __rows: Any
  __cols: Any

  def __init__(self, rows: Any, cols: Any) -> None:
    super().__init__(Matrix)
    self.__rows = rows
    self.__cols = cols

  @property
  def rows(self) -> Any:
    return self.__rows

  @property
  def cols(self) -> Any:
    return self.__cols

  def __str__(self) -> str:
    return "Matrix<%s, %s>" % (self.__rows, self.__cols)

  def signature_key(self) -> Any:
    return ("matrix_template", self.__rows, self.__cols)

  @cached_property
  def free_variables(self) -> frozenset[str]:
    free = set()
    if isinstance(self.__rows, str):
      free.add(self.__rows)
    if isinstance(self.__cols, str):
      free.add(self.__cols)
    return frozenset(free)

  def _resolve_dim(self, dim: Any, resolver: TypeResolver) -> Any:
    if isinstance(dim, str):
      return resolver.resolve_value_arg(dim, Matrix)
    return dim

  def resolve_type(self, resolver: TypeResolver, nesting_level: int = 0) -> Any:
    rows = self._resolve_dim(self.__rows, resolver)
    cols = self._resolve_dim(self.__cols, resolver)
    if isinstance(rows, range) or isinstance(cols, range):
      return _RequestMatrix(rows, cols)
    return Matrix(rows, cols)

  def extract_mappings(
    self,
    concrete_type: Any,
    possibles_values: Callable[[str], Any],
    rng: Random,
    types: dict[str, Any],
    args: dict[str, Any],
  ) -> Any:
    if not isinstance(concrete_type, Matrix):
      raise ValueError("Cannot extract mappings for non-matrix type: %s" % concrete_type)

    if isinstance(concrete_type, _RequestMatrix):
      concrete_rows, concrete_cols = concrete_type._rows, concrete_type._cols
    else:
      concrete_rows, concrete_cols = concrete_type.rows, concrete_type.cols

    rows = _extract_dim(self.__rows, concrete_rows, possibles_values, rng, args)
    cols = _extract_dim(self.__cols, concrete_cols, possibles_values, rng, args)
    return Matrix(rows, cols)


def _extract_dim(
  template_dim: Any,
  concrete: Any,
  possibles_values: Callable[[str], Any],
  rng: Random,
  args: dict[str, Any],
) -> int:
  if isinstance(template_dim, str):
    possible = possibles_values(template_dim)
    inter = intersection(possible, concrete)
    assert inter is not None, (
      "concrete dimension %s does not match possible %s for template variable %s"
      % (concrete, possible, template_dim)
    )
    value = rng.randint(inter.start, inter.stop - 1) if isinstance(inter, range) else inter
    args[template_dim] = value
    return int(value)

  if concrete is None:
    raise ValueError("cannot extract mappings from a matrix with an unspecified dimension")

  if isinstance(concrete, int):
    if template_dim != concrete:
      raise ValueError(
        "dimension mismatch for matrix template: expected %s, got %s" % (template_dim, concrete)
      )
    return int(concrete)

  if template_dim not in concrete:
    raise ValueError(
      "dimension %s not in allowed range %s for matrix template" % (template_dim, concrete)
    )
  return int(template_dim)


def matrix_specs() -> list[Any]:
  """The matrix function table: one shape-polymorphic spec per operation."""
  return [
    (
      FunctionSpecification(MATMUL)
      .with_generic_value("m", IRType.Field())
      .with_generic_value("k", IRType.Field())
      .with_generic_value("n", IRType.Field())
      .takes("a", MatrixTemplate("m", "k"))
      .takes("b", MatrixTemplate("k", "n"))
      .returns("c", MatrixTemplate("m", "n"))
      .constrained_by(RangeConstraint("m", MIN_DIM, MAX_DIM))
      .constrained_by(RangeConstraint("k", MIN_DIM, MAX_DIM))
      .constrained_by(RangeConstraint("n", MIN_DIM, MAX_DIM))
    ),
    (
      FunctionSpecification(ADD)
      .with_generic_value("m", IRType.Field())
      .with_generic_value("n", IRType.Field())
      .takes("a", MatrixTemplate("m", "n"))
      .takes("b", MatrixTemplate("m", "n"))
      .returns("c", MatrixTemplate("m", "n"))
      .constrained_by(RangeConstraint("m", MIN_DIM, MAX_DIM))
      .constrained_by(RangeConstraint("n", MIN_DIM, MAX_DIM))
    ),
    (
      FunctionSpecification(TRANSPOSE)
      .with_generic_value("m", IRType.Field())
      .with_generic_value("n", IRType.Field())
      .takes("a", MatrixTemplate("m", "n"))
      .returns("c", MatrixTemplate("n", "m"))
      .constrained_by(RangeConstraint("m", MIN_DIM, MAX_DIM))
      .constrained_by(RangeConstraint("n", MIN_DIM, MAX_DIM))
    ),
  ]
