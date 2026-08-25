"""Evaluate a CircIL circuit in Python, over the same field MP-SPDZ uses.

The point is to know whether a mutation changes the answer *before*
paying for a twin run. An injection that leaves every output identical is
inert by construction: the protocol has nothing to catch, and the run
teaches us nothing about soundness.

Inputs are bound the way `pipeline.translator` bakes them, so the values
here are the values the party binaries would compute.
"""
from __future__ import annotations

import pipeline.circil as _circil_path_setup  # noqa: F401
from typing import Any

from circil.ir.node import (  # type: ignore[import-not-found]
  Assignment,
  CallExpression,
  Identifier,
  Integer,
  LetExpression,
)

from pipeline.circil_ir import shape_of
from pipeline.matrix import ADD, FILL, MATMUL, TRANSPOSE
from pipeline.protocols import PRIME_MERSENNE_M127

FIELD = PRIME_MERSENNE_M127

Scalar = int
Grid = tuple[tuple[int, ...], ...]
Cell = Any


class Unevaluatable(Exception):
  """The circuit uses something this evaluator does not model."""


def _fill(rows: int, cols: int, value: Scalar) -> Grid:
  return tuple(tuple(value for _ in range(cols)) for _ in range(rows))


def _add(left: Grid, right: Grid) -> Grid:
  return tuple(
    tuple((a + b) % FIELD for a, b in zip(row_l, row_r))
    for row_l, row_r in zip(left, right)
  )


def _matmul(left: Grid, right: Grid) -> Grid:
  inner = range(len(right))
  return tuple(
    tuple(
      sum(row[i] * right[i][j] for i in inner) % FIELD
      for j in range(len(right[0]))
    )
    for row in left
  )


def _transpose(grid: Grid) -> Grid:
  return tuple(zip(*grid))


_MATRIX_OPS = {
  ADD: lambda args: _add(args[0], args[1]),
  MATMUL: lambda args: _matmul(args[0], args[1]),
  TRANSPOSE: lambda args: _transpose(args[0]),
}

_FIELD_OPS = {
  "+": lambda a, b: (a + b) % FIELD,
  "-": lambda a, b: (a - b) % FIELD,
  "*": lambda a, b: (a * b) % FIELD,
}


class _Evaluator:
  def __init__(self) -> None:
    self.names: dict[str, Cell] = {}

  def bind_inputs(self, circuit: Any) -> None:
    for index, signal in enumerate(circuit.inputs):
      literal = index + 1
      shape = shape_of(signal)
      if shape is None:
        self.names[signal.name] = literal
      elif shape.rows is None or shape.cols is None:
        raise Unevaluatable("input %r has no resolved shape" % signal.name)
      else:
        self.names[signal.name] = _fill(shape.rows, shape.cols, literal)

  def run(self, circuit: Any) -> dict[str, Cell]:
    self.bind_inputs(circuit)
    for statement in circuit.statements:
      if not isinstance(statement, Assignment):
        raise Unevaluatable("statement %r" % type(statement).__name__)
      self.names[statement.lhs.name] = self.value(statement.rhs)
    return {signal.name: self.names[signal.name] for signal in circuit.outputs}

  def value(self, node: Any) -> Cell:
    if isinstance(node, Integer):
      return node.value % FIELD
    if isinstance(node, Identifier):
      return self.names[node.name]
    if isinstance(node, LetExpression):
      self.names[node.var] = self.value(node.value)
      return self.value(node.body)
    if isinstance(node, CallExpression):
      return self.call(node)
    raise Unevaluatable("node %r" % type(node).__name__)

  def call(self, node: Any) -> Cell:
    name = node.function.name
    args = [self.value(argument) for argument in node.arguments]
    if name == FILL:
      shape = shape_of(node)
      if shape is None or shape.rows is None or shape.cols is None:
        raise Unevaluatable("matrix_fill with no shape")
      return _fill(shape.rows, shape.cols, args[0])
    if name in _MATRIX_OPS:
      return _MATRIX_OPS[name](args)
    if name in _FIELD_OPS:
      return _FIELD_OPS[name](args[0], args[1])
    raise Unevaluatable("call %r" % name)


def outputs_of(circuit: Any) -> dict[str, Cell]:
  """Every output's value, or `Unevaluatable` if the circuit is out of scope."""
  return _Evaluator().run(circuit)


def diverges(honest: Any, mutated: Any) -> bool:
  """True when the mutation actually changes a revealed output.

  An unevaluatable circuit counts as diverging: better to spend a run on
  a case we cannot pre-judge than to silently drop real coverage.
  """
  try:
    return outputs_of(honest) != outputs_of(mutated)
  except (Unevaluatable, KeyError, IndexError, ZeroDivisionError):
    return True
