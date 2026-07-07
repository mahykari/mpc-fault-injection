"""Drive the 8-combo disabled-Check()-sites campaign as one parallel launch.

Combo and seed are per-instance config: the 8 combos (subsets of
{subprocessor_check, beaver_check, private_output_check}) each get 2 instances,
so 16 instances total with unique ids i00..i15. Seeds are *paired* — the same
10k seed set (split into two 5k halves) and the same per-half expression_depth
are reused across every combo, so a given seed runs the identical program under
each combo and verdict shifts are attributable to the disabled check alone.

Runs against the instrumented image (MPSPDZ_DISABLED_SITES honoured at runtime);
launch.py spawns all 16 at once, then we aggregate every report into results.db
(each report carries its own combo label).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from itertools import combinations
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
IMAGE = "mpspdz-pipeline-seeded-bug:v0.4.2"
SITES = ["subprocessor_check", "beaver_check", "private_output_check"]

SEED = 0
HALF = 5000          # runs per instance; 2 instances per combo => 10k/combo
POOL = 100_000
MAX_DEPTH = 40

combos: list[list[str]] = [[]]
for r in range(1, len(SITES) + 1):
  combos.extend(list(c) for c in combinations(SITES, r))
labels = [",".join(c) if c else "baseline" for c in combos]


def build_plan() -> list[dict[str, Any]]:
  import random
  rng = random.Random(SEED)
  shared = rng.sample(range(POOL), 2 * HALF)
  halves = [shared[:HALF], shared[HALF:]]
  depths = [rng.randint(1, MAX_DEPTH), rng.randint(1, MAX_DEPTH)]
  plan: list[dict[str, Any]] = []
  iid = 0
  for label in labels:
    for h in range(2):
      plan.append({
        "instance_id": iid,
        "seeds": halves[h],
        "combo": label,
        "expression_depth": depths[h],
      })
      iid += 1
  return plan


def main() -> None:
  plan = build_plan()
  print(f"=== campaign: {len(labels)} combos x 2 instances = {len(plan)} instances, "
        f"{HALF} runs each ({len(plan) * HALF} total) ===", flush=True)

  with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
    json.dump(plan, f)
    plan_path = f.name

  subprocess.run([
    sys.executable, str(SCRIPT_DIR / "launch.py"),
    "--plan", plan_path, "--image", IMAGE,
  ], check=True)

  print("=== aggregating reports into results.db ===", flush=True)
  subprocess.run([
    sys.executable, str(REPO_ROOT / "main.py"), "aggregate",
  ], check=True)
  print("=== campaign complete ===")


if __name__ == "__main__":
  main()
