"""Run the pipeline on one or more seeds and dump per-party stdout/stderr.

Usage:
  uv run python -m exploration.dump_party_outputs 11 45 61 69 105 63 127

Mirrors run_pipeline (pipeline/__init__.py) but stops at the Executor
and prints per-party output. Useful for spotting things the verdict's
single summary field collapses away.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from pipeline import Config
from pipeline.compiler import Compiler
from pipeline.executor import Executor
from pipeline.gadgets import BumpTemplate, SignFlipTemplate
from pipeline.generator import generate_program
from pipeline.injector import Injector
from pipeline.mpspdz import MpSpdzCompilerToolkit, MpSpdzPartyBinary
from pipeline.translator import translate_to_mpspdz
from pipeline.types import Seed

REPO_ROOT = Path(__file__).resolve().parent.parent


PRIME_MERSENNE_M127 = 2**127 - 1


def run_seed(seed: int) -> None:
  config = Config(
    mpspdz_root=REPO_ROOT / "MP-SPDZ",
    runs_root=REPO_ROOT / "runs",
    seed=Seed(value=seed),
    protocol="mascot",
    n_parties=3,
    field_prime=PRIME_MERSENNE_M127,
    malicious_parties=[0, 1],
    timeout_s=30.0,
    use_patched_binary=True,
  )

  toolkit = MpSpdzCompilerToolkit(config)
  party_binary = MpSpdzPartyBinary(config)
  compiler = Compiler(toolkit, config)
  injector = Injector(toolkit, (BumpTemplate(), SignFlipTemplate()), config)
  executor = Executor(toolkit, party_binary, config)

  circil  = generate_program(config)
  mpspdz  = translate_to_mpspdz(circil)
  program = compiler.compile(mpspdz)
  mutated = injector.inject(mpspdz, program)
  run     = executor.execute(mutated)

  def dump(label: str, parties: tuple[Any, ...]) -> None:
    print()
    print(f"========== seed={seed:04d}  {label} ==========")
    for p in parties:
      print(f"--- party {p.party_id}  exit_code={p.exit_code} ---")
      print("[stdout]")
      print(p.stdout.rstrip() or "(empty)")
      print("[stderr]")
      print(p.stderr.rstrip() or "(empty)")

  dump("HONEST TWIN", run.honest_run)
  dump("MUTATED TWIN", run.mutated_run)


def main() -> None:
  seeds = [int(s) for s in sys.argv[1:]]
  if not seeds:
    print("usage: dump_party_outputs.py <seed> [seed ...]", file=sys.stderr)
    sys.exit(2)
  for seed in seeds:
    print()
    print("#" * 60)
    print(f"# seed={seed}")
    print("#" * 60)
    run_seed(seed)


if __name__ == "__main__":
  main()
