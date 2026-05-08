"""Stub: MP-SPDZ compiler (Python DSL → in-memory program IR).

Real impl will import MP-SPDZ's `Compiler` module and return its
`Compiler.program.Program` instance wrapped in `MpspdzProgram`.
For now: opaque handle (None) keyed only by program_id.
"""
from __future__ import annotations

from pipeline.types import MpspdzProgram, MpspdzSource


def compile_program(source: MpspdzSource) -> MpspdzProgram:
  print(
    f"[compiler] STUB: would compile {source.program_id} "
    f"({len(source.source)} bytes) via MP-SPDZ Compiler module"
  )
  return MpspdzProgram(program_id=source.program_id, ir_handle=None)
