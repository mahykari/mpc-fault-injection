"""Run the pipeline once and dump every party's stdout / stderr.

Mirrors run_pipeline (pipeline/__init__.py) but stops at the Executor
and prints per-party output instead of going through the Oracle +
Reporter. Useful for spotting things the verdict's single summary
field collapses away (e.g. "SECURITY BUG" lines, crashes, MAC
failures on individual parties).
"""
from __future__ import annotations

from pathlib import Path

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


def main() -> None:
  config = Config(
    mpspdz_root=REPO_ROOT / "MP-SPDZ",
    runs_root=REPO_ROOT / "runs",
    seed=Seed(value=100),
    protocol="mascot",
    n_parties=3,
    malicious_parties=(0, 1),
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

  def dump(label: str, parties: tuple) -> None:
    print()
    print(f"========== {label} ==========")
    for p in parties:
      print(f"--- party {p.party_id}  exit_code={p.exit_code} ---")
      print(f"[stdout]")
      print(p.stdout.rstrip() or "(empty)")
      print(f"[stderr]")
      print(p.stderr.rstrip() or "(empty)")

  dump("HONEST TWIN", run.honest_run)
  dump("MUTATED TWIN", run.mutated_run)


if __name__ == "__main__":
  main()
