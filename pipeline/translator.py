"""CircIL Circuit to MP-SPDZ Python DSL.

Subclasses CircIL's `EmptyVisitor`. Every expression visitor pushes
exactly one rendered string onto `_stack`; composing visitors pop their
operands. A plain stack rather than one flat text buffer because matrix
values cannot be expressed inline: `Matrix(r, c, sint)` is uninitialised
on construction and needs a following `assign_all`, so a matrix-valued
node emits statements and pushes the name of the temporary it built.

Field arithmetic stays inline, so scalar circuits emit the same shape of
source they always did.

Inputs are baked as literals rather than read from `Input-P<n>.<id>`
files: the twin run only needs determinism, and the seed-driven Circuit
already gives that.
"""
from __future__ import annotations

from typing import Any, Callable

import pipeline.circil as _circil_path_setup  # noqa: F401
from circil.ir.visitor import EmptyVisitor  # type: ignore[import-not-found]

from pipeline.circil_ir import shape_of
from pipeline.matrix import ADD, FILL, MATMUL, TRANSPOSE
from pipeline.types import CircilProgram, MpspdzSource

FIELD_OPS = {"+", "-", "*"}

# MP-SPDZ entry type for every secret value we emit.
VALUE_TYPE = "sint"


def _dims(shape: Any) -> tuple[int, int]:
  """Concrete (rows, cols), or a refusal.

  A shape still carrying `None` never resolved during generation, and
  emitting it would produce a `Matrix(None, ...)` that only fails later
  inside MP-SPDZ.
  """
  if shape.rows is None or shape.cols is None:
    raise NotImplementedError("matrix with unresolved shape: %s" % shape)
  return shape.rows, shape.cols


class MpspdzTranslation(EmptyVisitor):  # type: ignore[misc]
  def __init__(self) -> None:
    self.lines: list[str] = []
    self._stack: list[str] = []
    self._temps = 0

  # -- emission helpers -------------------------------------------------

  def _fresh(self) -> str:
    self._temps += 1
    return "_m%d" % self._temps

  def _bind(self, expression: str) -> str:
    """Assign `expression` to a fresh temporary and return its name."""
    name = self._fresh()
    self.lines.append("%s = %s" % (name, expression))
    return name

  def _operands(self, node: Any) -> list[str]:
    for argument in node.arguments:
      self.visit(argument)
    popped = [self._stack.pop() for _ in node.arguments]
    return list(reversed(popped))

  # -- matrix arms ------------------------------------------------------

  def _emit_fill(self, node: Any, operands: list[str]) -> str:
    shape = shape_of(node)
    if shape is None:
      raise NotImplementedError("matrix_fill with no resolved shape")
    rows, cols = _dims(shape)
    name = self._fresh()
    self.lines.append("%s = Matrix(%d, %d, %s)" % (name, rows, cols, VALUE_TYPE))
    self.lines.append("%s.assign_all(%s)" % (name, operands[0]))
    return name

  def _emit_add(self, node: Any, operands: list[str]) -> str:
    return self._bind("%s + %s" % (operands[0], operands[1]))

  def _emit_matmul(self, node: Any, operands: list[str]) -> str:
    return self._bind("%s.dot(%s)" % (operands[0], operands[1]))

  def _emit_transpose(self, node: Any, operands: list[str]) -> str:
    return self._bind("%s.transpose()" % operands[0])

  # Keyed by the CircIL function name so a new op is one table row.
  _MATRIX_ARMS: dict[str, Callable[[Any, Any, list[str]], str]] = {
    FILL: _emit_fill,
    ADD: _emit_add,
    MATMUL: _emit_matmul,
    TRANSPOSE: _emit_transpose,
  }

  # -- signals ----------------------------------------------------------

  def _bind_input(self, signal: Any, index: int) -> None:
    literal = "%s(%d)" % (VALUE_TYPE, index + 1)
    shape = shape_of(signal)
    if shape is None:
      self.lines.append("%s = %s" % (signal.name, literal))
      return
    rows, cols = _dims(shape)
    self.lines.append(
      "%s = Matrix(%d, %d, %s)" % (signal.name, rows, cols, VALUE_TYPE)
    )
    self.lines.append("%s.assign_all(%s)" % (signal.name, literal))

  def _reveal_output(self, signal: Any) -> None:
    revealed = "reveal_nested()" if shape_of(signal) is not None else "reveal()"
    self.lines.append(
      "print_ln('%s: %%s', %s.%s)" % (signal.name, signal.name, revealed)
    )

  # -- visitors ---------------------------------------------------------

  def visit_circuit(self, node: Any) -> None:
    for index, signal in enumerate(node.inputs):
      self._bind_input(signal, index)
    for statement in node.statements:
      self.visit(statement)
    for signal in node.outputs:
      self._reveal_output(signal)

  def visit_assignment(self, node: Any) -> None:
    self.visit(node.rhs)
    self.lines.append("%s = %s" % (node.lhs.name, self._stack.pop()))

  def visit_integer(self, node: Any) -> None:
    # A CircIL Integer in field position is a field element. Emitting a
    # plain Python int would propagate and break `.reveal()` downstream.
    self._stack.append("%s(%d)" % (VALUE_TYPE, node.value))

  def visit_identifier(self, node: Any) -> None:
    self._stack.append(node.name)

  def visit_call_expression(self, node: Any) -> None:
    name = node.function.name
    arm = self._MATRIX_ARMS.get(name)
    if arm is not None:
      self._stack.append(arm(self, node, self._operands(node)))
      return
    if name not in FIELD_OPS:
      raise NotImplementedError("unsupported op: %s" % name)
    operands = self._operands(node)
    if len(operands) != 2:
      raise NotImplementedError("op %s expects 2 args, got %d" % (name, len(operands)))
    self._stack.append("(%s %s %s)" % (operands[0], name, operands[1]))

  def visit_let_expression(self, node: Any) -> None:
    self.visit(node.value)
    self.lines.append("%s = %s" % (node.var, self._stack.pop()))
    self.visit(node.body)


def translate_to_mpspdz(program: CircilProgram) -> MpspdzSource:
  walker = MpspdzTranslation()
  walker.visit(program.circuit)
  source = "\n".join(walker.lines) + "\n"
  print("[translator] emitted %d lines of MP-SPDZ DSL:" % len(walker.lines))
  for line in walker.lines:
    print("  | %s" % line)
  return MpspdzSource(source=source)
