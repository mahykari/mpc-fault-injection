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

from pipeline.circil_ir import call
from pipeline.config import Config
from pipeline.generator import FIELD_MODULO
from pipeline.matrix import MATMUL, TRANSPOSE, Matrix
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


def _single_output_circuit(inputs: list[Any], result: Any, body: Any) -> Any:
  out = IRNode.Identifier("out", result)
  return IRNode.Circuit(
    "hand",
    FIELD_MODULO,
    list(inputs),
    [out.copy()],
    [IRNode.Assignment(out, body)],
  )


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
