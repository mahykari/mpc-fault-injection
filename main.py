"""Pipeline entrypoint.

`uv run python main.py` must always succeed. If it doesn't,
the pipeline invariant is broken (BLUEPRINT.md).
"""
from __future__ import annotations

from pathlib import Path

from pipeline import Config, run_pipeline
from pipeline.types import Seed

REPO_ROOT = Path(__file__).resolve().parent
MPSPDZ_ROOT = REPO_ROOT / "MP-SPDZ"
RUNS_ROOT = REPO_ROOT / "runs"


def main() -> None:
  config = Config(
    mpspdz_root=MPSPDZ_ROOT,
    runs_root=RUNS_ROOT,
    seed=Seed(value=42),
    protocol="mascot",
    n_parties=2,
    malicious_party=1,
    timeout_s=30.0,
    use_patched_binary=True,
  )
  report = run_pipeline(config)

  print()
  print("=== Config ===")
  print(f"  program_id:      {config.program_id}")
  print(f"  protocol:        {config.protocol}")
  print(f"  n_parties:       {config.n_parties}")
  print(f"  malicious_party: {config.malicious_party}")
  print(f"  run_dir:         {config.run_dir}")

  print()
  print("=== Report ===")
  print(f"  fault:       {report.fault}")
  print(f"  verdict:     {report.verdict}")
  print(f"  duration_ms: {report.duration_ms}")


if __name__ == "__main__":
  main()
