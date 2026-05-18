"""CircIL Circuit → MP-SPDZ Python DSL.

Subclasses CircIL's `EmptyVisitor`. The Generator's narrow FuzzerConfig
means we only see four node kinds: `Integer`, `Identifier`,
`CallExpression` (with op in `+ - *`), and `Assignment`. Anything else
is a config drift — we raise rather than guess.

Expression text is composed into a per-statement buffer (`_expr`):
leaf visitors append their atom, composing visitors wrap with brackets
and operators between child visits. At each `Assignment`, the buffer
is flushed into the line list.

Inputs are baked as `sint(<index+1>)` literals; we don't go through
`Input-P<n>.<id>` files because the twin-run only needs determinism,
and the seed-driven Circuit already gives us that.
"""
from __future__ import annotations

from typing import Any

import pipeline.circil as _circil_path_setup  # noqa: F401
from circil.ir.visitor import EmptyVisitor  # type: ignore[import-not-found]

from pipeline.types import CircilProgram, MpspdzSource


_OPS = {"+", "-", "*"}


class MpspdzTranslation(EmptyVisitor):  # type: ignore[misc]
  def __init__(self) -> None:
    self.lines: list[str] = []
    self._expr: list[str] = []

  def visit_circuit(self, node: Any) -> None:
    for idx, sig in enumerate(node.inputs):
      self.lines.append(f"{sig.name} = sint({idx + 1})")
    for stmt in node.statements:
      self.visit(stmt)
    for sig in node.outputs:
      self.lines.append(f"print_ln('{sig.name}: %s', {sig.name}.reveal())")

  def visit_assignment(self, node: Any) -> None:
    self._expr = []
    self.visit(node.rhs)
    self.lines.append(f"{node.lhs.name} = {''.join(self._expr)}")

  def visit_integer(self, node: Any) -> None:
    # CircIL `Integer` in a Field context is a field element; emit as
    # `sint(<value>)` so any expression with at least one constant
    # operand still produces an sint downstream. (Plain Python `int`
    # would propagate and break `.reveal()` at the output.)
    self._expr.append(f"sint({node.value})")

  def visit_identifier(self, node: Any) -> None:
    self._expr.append(node.name)

  def visit_call_expression(self, node: Any) -> None:
    op = node.function.name
    if op not in _OPS:
      raise NotImplementedError(f"unsupported op: {op}")
    if len(node.arguments) != 2:
      raise NotImplementedError(f"op {op} expects 2 args, got {len(node.arguments)}")
    self._expr.append("(")
    self.visit(node.arguments[0])
    self._expr.append(f" {op} ")
    self.visit(node.arguments[1])
    self._expr.append(")")

  def visit_let_expression(self, node: Any) -> None:
    buffer = self._expr
    self._expr = []
    self.visit(node.value)
    self.lines.append(f"{node.var} = {''.join(self._expr)}")
    self._expr = buffer
    self.visit(node.body)


def translate_to_mpspdz(program: CircilProgram) -> MpspdzSource:
  walker = MpspdzTranslation()
  walker.visit(program.circuit)
  print(f"[translator] emitted {len(walker.lines)} lines of MP-SPDZ DSL")
  return MpspdzSource(source="\n".join(walker.lines) + "\n")
