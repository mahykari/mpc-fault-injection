"""Print the CircIL programs our Generator emits, for a few seeds.

Useful to eyeball what `SimpleCircuitFuzzer` is producing under our
stripped FuzzerConfig (Field-only, +/-/*, no arrays/lambdas/let).
Run from repo root: `uv run python exploration/show_circil_programs.py`.
"""
from __future__ import annotations

from pipeline.config import Config
from pipeline.generator import generate_program
from pipeline.types import Seed
from pathlib import Path


def main() -> None:
  for seed in (42, 100, 7, 2026):
    config = Config(
      mpspdz_root=Path("MP-SPDZ"),
      runs_root=Path("runs"),
      seed=Seed(value=seed),
      protocol="mascot",
      n_parties=2,
      malicious_party=1,
      timeout_s=30.0,
      use_patched_binary=True,
    )
    program = generate_program(config)
    print(f"\n--- seed={seed} ---")
    print(program.circuit)


if __name__ == "__main__":
  main()
