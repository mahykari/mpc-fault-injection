"""Shared fixtures and the one-line check reporter.

Nothing here touches MP-SPDZ: `matrix_config` points the run paths at a
throwaway tmpdir that is never created, because generation and checking
are pure in-memory work.
"""
from __future__ import annotations

import pipeline.circil as _circil_path_setup  # noqa: F401
import tempfile
from pathlib import Path
from typing import Any

import circil.ir.node as IRNode  # type: ignore[import-not-found]

import contextlib
import io

from pipeline.circil_ir import call
from pipeline.config import Config
from pipeline.generator import FIELD_MODULO, generate_program
from pipeline.matrix import ADD, MATMUL, TRANSPOSE, Matrix
from pipeline.types import Seed

_SCRATCH = Path(tempfile.gettempdir()) / "pipeline-tests"


class CheckFailed(AssertionError):
  pass


def expect(ok: bool, label: str) -> None:
  print(("  ok   " if ok else "  FAIL ") + label)
  if not ok:
    raise CheckFailed(label)


def matrix_config(seed: int) -> Config:
  return Config(
    mpspdz_root=_SCRATCH / "MP-SPDZ",
    runs_root=_SCRATCH / "runs",
    seed=Seed(seed),
    protocol="mascot",
    n_parties=2,
    malicious_parties=[1],
    timeout_s=60.0,
    program_family="matrix",
  )


def generated(seed: int) -> Any:
  # The generator logs a line per circuit; a batch would bury the checks.
  with contextlib.redirect_stdout(io.StringIO()):
    return generate_program(matrix_config(seed)).circuit


def _circuit(inputs: list[Any], outputs: list[Any], statements: list[Any]) -> Any:
  return IRNode.Circuit(
    "hand",
    0,
    "hand-built",
    FIELD_MODULO,
    [signal.copy() for signal in inputs],
    [signal.copy() for signal in outputs],
    statements,
  )


def _single_output_circuit(inputs: list[Any], result: Any, body: Any) -> Any:
  out = IRNode.Identifier("out", result)
  return _circuit(inputs, [out], [IRNode.Assignment(out, body)])


def hand_transpose_of_product() -> Any:
  left = IRNode.Identifier("a", Matrix(2, 3))
  right = IRNode.Identifier("b", Matrix(3, 2))
  product = call(MATMUL, [left, right], Matrix(2, 2))
  return _single_output_circuit(
    [left.copy(), right.copy()],
    Matrix(2, 2),
    call(TRANSPOSE, [product], Matrix(2, 2)),
  )


def hand_double_transpose() -> Any:
  operand = IRNode.Identifier("a", Matrix(2, 3))
  inner = call(TRANSPOSE, [operand], Matrix(3, 2))
  return _single_output_circuit(
    [operand.copy()],
    Matrix(2, 3),
    call(TRANSPOSE, [inner], Matrix(2, 3)),
  )


def hand_add() -> Any:
  left = IRNode.Identifier("a", Matrix(2, 3))
  right = IRNode.Identifier("b", Matrix(2, 3))
  return _single_output_circuit(
    [left.copy(), right.copy()],
    Matrix(2, 3),
    call(ADD, [left, right], Matrix(2, 3)),
  )


def hand_let_scoped() -> Any:
  """`t = (madd a b); out = (madd t (let x = a in x))`.

  Exercises the donor filters: `x` is bound inside the site, `t` is
  assigned before it, and the enclosing `madd` is an ancestor.
  """
  shape = Matrix(2, 3)
  left = IRNode.Identifier("a", shape)
  right = IRNode.Identifier("b", shape)
  temp = IRNode.Identifier("t", shape)
  out = IRNode.Identifier("out", shape)
  bound = IRNode.LetExpression("x", left.copy(), IRNode.Identifier("x", shape))
  return _circuit(
    [left, right],
    [out],
    [
      IRNode.Assignment(temp.copy(), call(ADD, [left.copy(), right.copy()], shape)),
      IRNode.Assignment(out.copy(), call(ADD, [temp.copy(), bound], shape)),
    ],
  )
