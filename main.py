"""Pipeline entrypoint, for the host and inside a container.

`uv run python main.py` runs (BLUEPRINT invariant): with no env set it
runs seeds 0..N_RUNS-1 as instance 0 with DEFAULTS. Env overrides:
  INSTANCE_ID  instance index; namespaces run artifacts   (default 0)
  SEEDS        comma-separated seeds to run               (default range(N_RUNS))
  CONFIG       path to a partial JSON config overlaid on DEFAULTS (default none)
"""
from __future__ import annotations

import os
from pathlib import Path

from pipeline import Config
from pipeline.campaign import run_campaign
from pipeline.config import load_overrides
from pipeline.types import Seed

REPO_ROOT = Path(__file__).resolve().parent
MPSPDZ_ROOT = REPO_ROOT / "MP-SPDZ"
RUNS_ROOT = REPO_ROOT / "runs"

N_RUNS = 200

PRIME_MERSENNE_M127 = 2**127 - 1

DEFAULTS = Config(
  mpspdz_root=MPSPDZ_ROOT,
  runs_root=RUNS_ROOT,
  seed=Seed(value=0),
  protocol="mascot",
  n_parties=3,
  field_prime=PRIME_MERSENNE_M127,
  malicious_parties=(0, 1),
  timeout_s=30.0,
  use_patched_binary=True,
  seeded_bug_binary=False,
)


def _seeds() -> list[int]:
  raw = os.environ.get("SEEDS", "").strip()
  if raw:
    return [int(s) for s in raw.split(",")]
  return list(range(N_RUNS))


def _base_config() -> Config:
  path = os.environ.get("CONFIG")
  return load_overrides(DEFAULTS, Path(path)) if path else DEFAULTS


def main() -> None:
  run_campaign(
    _base_config(),
    _seeds(),
    instance_id=int(os.environ.get("INSTANCE_ID", "0")),
  )


if __name__ == "__main__":
  main()
