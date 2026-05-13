"""End-to-end pipeline driver.

Wires the seven components together. Stubs and real implementations
coexist; the pipeline always runs end-to-end (BLUEPRINT.md invariant).
"""
from __future__ import annotations

from pipeline.compiler import Compiler
from pipeline.config import Config
from pipeline.executor import Executor
from pipeline.gadgets import SingleVariableBumpTemplate
from pipeline.generator import generate_program
from pipeline.injector import Injector
from pipeline.mpspdz import MpSpdzCompilerToolkit, MpSpdzPartyBinary
from pipeline.oracle import judge
from pipeline.reporter import report
from pipeline.translator import translate_to_mpspdz
from pipeline.types import Report


def run_pipeline(config: Config) -> Report:
  toolkit = MpSpdzCompilerToolkit(config)
  party_binary = MpSpdzPartyBinary(config)
  compiler = Compiler(toolkit, config)
  injector = Injector(toolkit, (SingleVariableBumpTemplate(),), config)
  executor = Executor(toolkit, party_binary, config)

  circil  = generate_program(config)
  mpspdz  = translate_to_mpspdz(circil)
  program = compiler.compile(mpspdz)
  mutated = injector.inject(mpspdz, program)
  run     = executor.execute(mutated)
  verdict = judge(run)
  return report(mutated, run, verdict, config)


__all__ = ["Config", "run_pipeline"]
