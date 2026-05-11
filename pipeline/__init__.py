"""End-to-end pipeline driver.

Wires the seven components together. Each is a stub at scaffold time;
real implementations replace stubs one at a time, never breaking the
end-to-end run (BLUEPRINT.md invariant).
"""
from __future__ import annotations

from pipeline.compiler import Compiler
from pipeline.config import Config
from pipeline.executor import Executor
from pipeline.generator import generate_program, translate_to_mpspdz
from pipeline.injector import inject_fault
from pipeline.mpspdz import MpSpdzCompilerToolkit, MpSpdzPartyBinary
from pipeline.oracle import judge
from pipeline.reporter import report
from pipeline.types import Report


def run_pipeline(config: Config) -> Report:
  toolkit = MpSpdzCompilerToolkit(config)
  party_binary = MpSpdzPartyBinary(config)
  compiler = Compiler(toolkit, config)
  executor = Executor(party_binary, config)

  circil  = generate_program(config)
  mpspdz  = translate_to_mpspdz(circil)
  program = compiler.compile(mpspdz)
  mutated = inject_fault(program, config)
  run     = executor.execute(mutated)
  verdict = judge(run)
  return report(mutated, run, verdict, config)


__all__ = ["Config", "run_pipeline"]
