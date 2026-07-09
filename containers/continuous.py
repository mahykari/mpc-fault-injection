"""Continuous fuzzing: repeated N-instance rounds until a run cap (or forever).

Each round launches `--instances` pipeline containers of `--runs` runs each,
aggregates every round into results.db, then advances to a fresh disjoint seed
window so no seed (hence no program, no case id) repeats across rounds. Aggregate
is idempotent, so results accumulate; the loop survives a bad round (a crashed
container fails that round, not the campaign).

`--protocols` spreads the given protocols round-robin across instances, each with
the corrupt-set size its threshold model allows (honest-majority gets fewer), and
the verdict rows carry the protocol so one results.db holds them all. `--memory`
caps per-instance RAM so a long unattended run can't exhaust the host; other
tunables ride through `--config`.

Build the image, then fire and walk away:
  ./containers/build.sh pipeline
  uv run python containers/continuous.py --memory 4g --max-runs 500000
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.protocols import PROTOCOL_SPECS  # noqa: E402  (needs REPO_ROOT on path)

IMAGE = "mpspdz-pipeline:v0.4.2"
MAX_DEPTH = 40


def parse_args() -> argparse.Namespace:
  p = argparse.ArgumentParser(description=__doc__)
  p.add_argument("--instances", type=int, default=16)
  p.add_argument("--runs", type=int, default=200, help="runs per instance per round")
  p.add_argument("--max-runs", type=int, help="stop once cumulative runs reach this (default: unbounded)")
  p.add_argument("--protocols", default="mascot,spdz2k,malicious-shamir",
                 help="comma-separated protocols spread round-robin across instances")
  p.add_argument("--n-parties", type=int, default=3)
  p.add_argument("--start-seed", type=int, default=0, help="first seed; windows advance from here")
  p.add_argument("--image", default=IMAGE)
  p.add_argument("--memory", default="4g", help="podman --memory per instance")
  p.add_argument("--cpus", help="podman --cpus per instance")
  p.add_argument("--config", help="JSON file of tunables merged into every spec (e.g. protocol)")
  return p.parse_args()


def build_plan(
  instances: int, runs: int, round_idx: int, start_seed: int,
  protocols: list[str], n_parties: int,
) -> list[dict[str, Any]]:
  rng = random.Random(round_idx)
  base = start_seed + round_idx * instances * runs
  plan = []
  for i in range(instances):
    lo = base + i * runs
    protocol = protocols[i % len(protocols)]
    corrupt = PROTOCOL_SPECS[protocol].max_corrupt(n_parties)
    plan.append({
      "instance_id": i,
      "seeds": list(range(lo, lo + runs)),
      "combo": "baseline",
      "protocol": protocol,
      "n_parties": n_parties,
      "malicious_parties": list(range(corrupt)),
      "expression_depth": rng.randint(1, MAX_DEPTH),
    })
  return plan


def launch_cmd(args: argparse.Namespace, plan_path: str) -> list[str]:
  cmd = [
    sys.executable, str(SCRIPT_DIR / "launch.py"),
    "--plan", plan_path, "--image", args.image, "--memory", args.memory,
  ]
  if args.cpus:
    cmd += ["--cpus", args.cpus]
  if args.config:
    cmd += ["--config", args.config]
  return cmd


def main() -> None:
  args = parse_args()
  protocols = [p.strip() for p in args.protocols.split(",") if p.strip()]
  total = 0
  round_idx = 0
  while args.max_runs is None or total < args.max_runs:
    plan = build_plan(
      args.instances, args.runs, round_idx, args.start_seed, protocols, args.n_parties)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
      json.dump(plan, f)
      plan_path = f.name

    print(f"=== round {round_idx}: {args.instances} instances x {args.runs} runs ===", flush=True)
    code = subprocess.run(launch_cmd(args, plan_path)).returncode
    if code != 0:
      print(f"--- round {round_idx}: launch exit {code} (continuing) ---", flush=True)
    subprocess.run([sys.executable, str(REPO_ROOT / "main.py"), "aggregate"])

    total += args.instances * args.runs
    round_idx += 1
    print(f"=== {round_idx} rounds, ~{total} runs cumulative ===", flush=True)

  print("=== run cap reached ===")


if __name__ == "__main__":
  main()
