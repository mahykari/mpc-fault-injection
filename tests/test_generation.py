"""Unit 1: matrix circuits generate well-shaped, and repeat on a seed."""
from __future__ import annotations

import contextlib
import io
from collections import Counter
from typing import Any

from pipeline.check import CircuitTypeError, call_names, check_circuit
from pipeline.generator import generate_program
from pipeline.matrix import MADD, MATMUL, TRANSPOSE, Matrix, matrix_specs
from tests.support import (
  expect,
  hand_double_transpose,
  hand_transpose_of_product,
  matrix_config,
)

BATCH = 200
REPEAT_SEEDS = (0, 1, 7, 11, 42)


def _generate(seed: int) -> Any:
  # The generator logs a line per circuit; the batch would bury the checks.
  with contextlib.redirect_stdout(io.StringIO()):
    return generate_program(matrix_config(seed)).circuit


def _fingerprint(circuit: Any) -> list[str]:
  return (
    [str(i) for i in circuit.inputs]
    + [str(o) for o in circuit.outputs]
    + [str(s) for s in circuit.statements]
  )


def _spec_table_consistent() -> bool:
  for spec in matrix_specs():
    operands = [infos.type_spec for _, infos in spec.parameters]
    result = spec.return_type()
    if spec.name == MATMUL:
      left, right = operands
      ok = (left.cols == right.rows
            and result.rows == left.rows and result.cols == right.cols)
    elif spec.name == MADD:
      left, right = operands
      ok = bool(left.equiv(right)) and bool(left.equiv(result))
    elif spec.name == TRANSPOSE:
      operand = operands[0]
      ok = result.rows == operand.cols and result.cols == operand.rows
    else:
      ok = False
    if not all(isinstance(t, Matrix) for t in operands + [result]) or not ok:
      return False
  return True


def run() -> None:
  print("test_generation")

  expect(len(matrix_specs()) == 16, "matrix_specs has 16 concrete specs")
  expect(_spec_table_consistent(), "every spec's result shape follows from its operands")

  seen: Counter[str] = Counter()
  violations: list[str] = []
  for seed in range(BATCH):
    circuit = _generate(seed)
    try:
      check_circuit(circuit)
    except CircuitTypeError as failure:
      violations.append("seed %d: %s" % (seed, failure))
      continue
    seen += call_names(circuit)
  for bad in violations[:3]:
    print("    " + bad)
  expect(not violations, "%d generated circuits typecheck" % BATCH)
  expect(seen[MATMUL] > 0, "batch contains matmul (%d)" % seen[MATMUL])
  expect(seen[MADD] > 0, "batch contains madd (%d)" % seen[MADD])
  expect(seen[TRANSPOSE] > 0, "batch contains transpose (%d)" % seen[TRANSPOSE])

  mismatched = [s for s in REPEAT_SEEDS
                if _fingerprint(_generate(s)) != _fingerprint(_generate(s))]
  expect(not mismatched, "same seed generates an identical circuit twice")

  for name, circuit in (("transpose of product", hand_transpose_of_product()),
                        ("double transpose", hand_double_transpose())):
    ok = True
    try:
      check_circuit(circuit)
    except CircuitTypeError:
      ok = False
    expect(ok, "hand-built %s typechecks" % name)
