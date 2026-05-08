"""End-to-end pipeline driver.

Wires the seven components together. Each is a stub at scaffold time;
real implementations replace stubs one at a time, never breaking the
end-to-end run (BLUEPRINT.md invariant).
"""
from __future__ import annotations

from pipeline.compiler import compile_program
from pipeline.executor import execute
from pipeline.generator import generate_program, translate_to_mpspdz
from pipeline.injector import inject_fault
from pipeline.oracle import judge
from pipeline.reporter import report
from pipeline.types import Protocol, Report, Seed


def run_pipeline(
  seed: Seed,
  protocol: Protocol = "mascot",
  n_parties: int = 2,
  malicious_party: int = 1,
) -> Report:
  circil = generate_program(seed)
  mpspdz = translate_to_mpspdz(circil)
  program = compile_program(mpspdz)
  mutated = inject_fault(program, seed, malicious_party=malicious_party)
  run = execute(
    mutated,
    protocol=protocol,
    n_parties=n_parties,
    malicious_party=malicious_party,
  )
  verdict = judge(run)
  return report(mutated, run, verdict)


__all__ = ["run_pipeline"]
