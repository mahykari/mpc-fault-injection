"""Low-level pokes at CircIL IR nodes.

python-circil ships no stubs and its node constructors want positional
`FunctionDefinition` plumbing; that ugliness is confined here so call
sites read as `call(MATMUL, [a, b], Matrix(2, 3))`.
"""
from __future__ import annotations

import pipeline.circil as _circil_path_setup  # noqa: F401
from typing import Any

import circil.ir.types as IRType  # type: ignore[import-not-found]
from circil.ir.node import (  # type: ignore[import-not-found]
  CallExpression,
  Expression,
  FunctionDefinition,
  Integer,
)

from pipeline.matrix import Matrix


def call(name: str, args: list[Any], result: Any) -> Any:
  return CallExpression(
    FunctionDefinition(
      name,
      parameters=tuple(("x%d" % i, a.type_hint) for i, a in enumerate(args)),
      template_parameters=(),
      result=result,
    ),
    list(args),
    template_arguments=[],
  )


def is_call(node: Any, name: str) -> bool:
  return isinstance(node, CallExpression) and bool(node.function.name == name)


def type_of(node: Any) -> Any | None:
  """The node's type, or None when it has none or cannot compute one.

  `ArrayLiteral.type_hint` raises on heterogeneous elements and
  `ArrayAccess.type_hint` asserts on a non-array base; neither is an
  error we care about, both just mean "no usable type here".
  """
  if not isinstance(node, Expression):
    return None
  try:
    return node.type_hint
  except (TypeError, AssertionError):
    return None


def shape_of(node: Any) -> Matrix | None:
  found = type_of(node)
  return found if isinstance(found, Matrix) else None


def is_field(node: Any) -> bool:
  found = type_of(node)
  return found is not None and bool(found.equiv(IRType.Field())) and not found.is_generic


def integer(value: int) -> Any:
  return Integer(value)
