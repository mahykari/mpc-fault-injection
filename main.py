"""Pipeline entrypoint, for the host and inside a container.

`uv run python main.py` runs (BLUEPRINT invariant). With no env it runs
seeds 0..N_RUNS-1 as instance 0 with DEFAULTS. The `CONFIG` env points at a
JSON run spec (written per-instance by the launcher) carrying everything:
  seeds        list of seeds this run executes      (default range(N_RUNS))
  instance_id  namespaces run artifacts             (default 0)
  <other keys> Config-field overrides onto DEFAULTS (e.g. expression_depth)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pipeline import Config
from pipeline.campaign import run_campaign
from pipeline.config import apply_overrides
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
  malicious_parties=[0, 1],
  timeout_s=30.0,
  use_patched_binary=True,
  seeded_bug_binary=False,
)


def _spec() -> dict[str, Any]:
  path = os.environ.get("CONFIG")
  return json.loads(Path(path).read_text()) if path else {}


def main() -> None:
  spec = _spec()
  seeds = spec.pop("seeds", list(range(N_RUNS)))
  instance_id = spec.pop("instance_id", 0)
  run_campaign(apply_overrides(DEFAULTS, spec), seeds, instance_id)


if __name__ == "__main__":
  main()
