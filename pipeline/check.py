"""Shape/scope typechecker for generated CircIL circuits.

The fuzzer is trusted to emit well-typed circuits, but a wrong row in
the matrix spec table (or, later, a bad rewrite) produces a silently
mis-shaped circuit rather than an error. This walker is the gate that
turns that into a failure.
"""
from __future__ import annotations

import pipeline.circil as _circil_path_setup  # noqa: F401
from collections import Counter
from typing import Any, Callable

import circil.ir.types as IRType  # type: ignore[import-not-found]
from circil.ir.node import (  # type: ignore[import-not-found]
  CallExpression,
  Identifier,
)
from circil.ir.visitor import IRWalker  # type: ignore[import-not-found]

from pipeline.matrix import FILL, ADD, MATMUL, TRANSPOSE, Matrix


class CircuitTypeError(Exception):
  pass


CallRule = Callable[[list[Any], Any], bool]


def _matmul_ok(args: list[Any], result: Any) -> bool:
  if len(args) != 2:
    return False
  left, right = args
  return (
    isinstance(left, Matrix) and isinstance(right, Matrix) and isinstance(result, Matrix)
    and left.cols == right.rows
    and result.rows == left.rows and result.cols == right.cols
  )


def _madd_ok(args: list[Any], result: Any) -> bool:
  if len(args) != 2:
    return False
  left, right = args
  return isinstance(left, Matrix) and bool(left.equiv(right)) and bool(left.equiv(result))


def _transpose_ok(args: list[Any], result: Any) -> bool:
  if len(args) != 1:
    return False
  operand = args[0]
  return (
    isinstance(operand, Matrix) and isinstance(result, Matrix)
    and result.rows == operand.cols and result.cols == operand.rows
  )


def _fill_ok(args: list[Any], result: Any) -> bool:
  return len(args) == 1 and bool(args[0].equiv(IRType.Field())) and isinstance(result, Matrix)


def _field_op_ok(args: list[Any], result: Any) -> bool:
  field = IRType.Field()
  return len(args) == 2 and all(bool(t.equiv(field)) for t in args + [result])


CALL_RULES: dict[str, CallRule] = {
  MATMUL: _matmul_ok,
  ADD: _madd_ok,
  TRANSPOSE: _transpose_ok,
  FILL: _fill_ok,
  "+": _field_op_ok,
  "-": _field_op_ok,
  "*": _field_op_ok,
}


class CircuitChecker(IRWalker):  # type: ignore[misc]
  calls: int
  names: Counter[str]

  def __init__(self) -> None:
    self.calls = 0
    self.names = Counter()
    self._scope: list[str] = []

  def visit(self, node: Any) -> None:
    if isinstance(node, CallExpression):
      self._check_call(node)
    if isinstance(node, Identifier) and node.name not in self._scope:
      raise CircuitTypeError("out of scope: %s" % node.name)
    super().visit(node)

  def _check_call(self, node: Any) -> None:
    self.calls += 1
    name = str(node.function.name)
    self.names[name] += 1
    rule = CALL_RULES.get(name)
    if rule is None:
      raise CircuitTypeError("unknown function: %s" % name)
    if not rule([a.type_hint for a in node.arguments], node.function.result):
      raise CircuitTypeError("ill-typed %s: %s" % (name, node))

  def visit_assignment(self, node: Any) -> None:
    self.visit(node.rhs)
    self._scope.append(node.lhs.name)

  def visit_let_expression(self, node: Any) -> None:
    if node.value is not None:
      self.visit(node.value)
    self._scope.append(node.var)
    self.visit(node.body)
    self._scope.pop()

  def visit_circuit(self, node: Any) -> None:
    self._scope = [i.name for i in node.inputs]
    for statement in node.statements:
      self.visit(statement)


def _checked(circuit: Any) -> CircuitChecker:
  """Run the checker over `circuit` and hand back what it collected."""
  checker = CircuitChecker()
  checker.visit(circuit)
  return checker


def check_circuit(circuit: Any) -> int:
  return _checked(circuit).calls


def call_names(circuit: Any) -> Counter[str]:
  return _checked(circuit).names
