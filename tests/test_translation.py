"""Unit: matrix circuits translate to MP-SPDZ DSL, and that DSL compiles.

The compile checks need MP-SPDZ on disk. It is gitignored and per-machine,
so they report as skipped rather than failing when it is absent.
"""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
from typing import Any

from tests.support import expect, generated, matrix_config

from pipeline.matrix import ADD, FILL, MATMUL, TRANSPOSE
from pipeline.rewrite import rewrite_circuit
from pipeline.translator import translate_to_mpspdz
from pipeline.types import CircilProgram

BATCH = 12
COMPILE_BATCH = 8

REPO_ROOT = Path(__file__).resolve().parent.parent
MPSPDZ_ROOT = REPO_ROOT / "MP-SPDZ"


def _translate(circuit: Any) -> str:
  with contextlib.redirect_stdout(io.StringIO()):
    return translate_to_mpspdz(CircilProgram(circuit=circuit)).source


def _compile_sources(sources: list[str]) -> list[str]:
  """Returns one failure description per source that did not compile."""
  from pipeline.mpspdz import MpSpdzCompilerToolkit

  config = matrix_config(0)
  toolkit = MpSpdzCompilerToolkit(_with_root(config))
  failures = []
  for index, source in enumerate(sources):
    try:
      with contextlib.redirect_stdout(io.StringIO()):
        toolkit.compile("suite-%d" % index, source)
    except Exception as failure:
      failures.append("%d: %s: %s" % (index, type(failure).__name__, str(failure)[:120]))
  return failures


def _with_root(config: Any) -> Any:
  import dataclasses

  return dataclasses.replace(config, mpspdz_root=MPSPDZ_ROOT)


def run() -> None:
  print("test_translation")

  with contextlib.redirect_stdout(io.StringIO()):
    circuits = [generated(seed) for seed in range(BATCH)]

  sources = [_translate(circuit) for circuit in circuits]
  expect(len(sources) == BATCH, "%d matrix circuits translate" % BATCH)

  joined = "\n".join(sources)
  for name, token in (
    ("matrix construction", "Matrix("),
    ("fill", ".assign_all("),
    (MATMUL, ".dot("),
    (TRANSPOSE, ".transpose()"),
    ("reveal", ".reveal_nested()"),
  ):
    expect(token in joined, "emitted source uses %s" % name)

  rewritten = [rewrite_circuit(c, seed=i, amount=2).circuit for i, c in enumerate(circuits)]
  rewritten_sources = [_translate(c) for c in rewritten]
  expect(len(rewritten_sources) == BATCH, "%d rewritten circuits translate" % BATCH)

  if not (MPSPDZ_ROOT / "Compiler").is_dir():
    print("  skip MP-SPDZ compile checks (no MP-SPDZ/ on disk)")
    return

  failures = _compile_sources(sources[:COMPILE_BATCH])
  for bad in failures[:3]:
    print("    " + bad)
  expect(not failures, "%d translated circuits compile" % COMPILE_BATCH)

  failures = _compile_sources(rewritten_sources[:COMPILE_BATCH])
  for bad in failures[:3]:
    print("    " + bad)
  expect(not failures, "%d rewritten circuits compile" % COMPILE_BATCH)
