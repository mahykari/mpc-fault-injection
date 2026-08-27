"""A small campaign on the host, no containers, for a quick verdict spread.

Useful before committing a change to a 1000-case containerised run.

Run from the repo root:  PYTHONPATH=. uv run python exploration/local_campaign.py 10
"""
import sys
from pathlib import Path
from pipeline import Config
from pipeline.instance import run_instance
from pipeline.types import Seed

ROOT = Path("/home/mkarimi/matrix-rewrites")
n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
run_instance(Config(
  mpspdz_root=ROOT / "MP-SPDZ", runs_root=Path("/tmp/local-batch"), seed=Seed(0),
  protocol="mascot", n_parties=2, malicious_parties=[1], timeout_s=120.0,
  use_patched_binary=True, program_family="matrix", injection_layer="source",
), range(n), instance_id=0)
