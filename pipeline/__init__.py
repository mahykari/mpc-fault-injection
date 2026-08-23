"""End-to-end pipeline driver.

Wires the seven components together. Stubs and real implementations
coexist; the pipeline always runs end-to-end (BLUEPRINT.md invariant).
"""
from __future__ import annotations

from typing import Any

from pipeline.compiler import Compiler
from pipeline.config import Config
from pipeline.executor import Executor
from pipeline.gadgets import BumpTemplate, SignFlipTemplate
from pipeline.generator import generate_program
from pipeline.injector import Injector
from pipeline.mpspdz import MpSpdzCompilerToolkit, MpSpdzPartyBinary, SslProvisioner
from pipeline.oracle import judge
from pipeline.reporter import report
from pipeline.source_injector import SourceInjector
from pipeline.translator import translate_to_mpspdz
from pipeline.types import CircilProgram, InjectionLayer, MutatedProgram, Report


def _inject_bytecode(
  config: Config, toolkit: MpSpdzCompilerToolkit, compiler: Compiler,
  circil: CircilProgram, mpspdz: Any, program: Any,
) -> MutatedProgram:
  """Retired path: mutate the compiled tape. Kept for the field family."""
  injector = Injector(toolkit, (BumpTemplate(), SignFlipTemplate()), config)
  return injector.inject(mpspdz, program)


def _inject_source(
  config: Config, toolkit: MpSpdzCompilerToolkit, compiler: Compiler,
  circil: CircilProgram, mpspdz: Any, program: Any,
) -> MutatedProgram:
  return SourceInjector(toolkit, compiler, config).inject(circil, program)


_INJECTORS: dict[InjectionLayer, Any] = {
  "bytecode": _inject_bytecode,
  "source": _inject_source,
}


def run_pipeline(config: Config) -> Report:
  toolkit = MpSpdzCompilerToolkit(config)
  party_binary = MpSpdzPartyBinary(config)
  compiler = Compiler(toolkit, config)
  ssl = SslProvisioner(config)
  executor = Executor(toolkit, party_binary, ssl, config)

  circil  = generate_program(config)
  mpspdz  = translate_to_mpspdz(circil)
  program = compiler.compile(mpspdz)
  mutated = _INJECTORS[config.injection_layer](
    config, toolkit, compiler, circil, mpspdz, program)
  run     = executor.execute(mutated)
  verdict = judge(run, config)
  return report(mutated, run, verdict, config)


__all__ = ["Config", "run_pipeline"]
