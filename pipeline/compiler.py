"""Compiler component: MP-SPDZ DSL source → in-memory Program."""
from __future__ import annotations

from pipeline.config import NeedsCompiler
from pipeline.mpspdz import MpSpdzCompilerToolkit
from pipeline.types import MpspdzProgram, MpspdzSource


class Compiler:
  def __init__(
    self, toolkit: MpSpdzCompilerToolkit, config: NeedsCompiler,
  ) -> None:
    self._toolkit = toolkit
    self._config = config

  def compile(self, source: MpspdzSource) -> MpspdzProgram:
    print(f"[compiler] {self._config.program_id}: lowering DSL → IR")
    program = self._toolkit.compile(self._config.program_id, source.source)
    return MpspdzProgram(program=program)
