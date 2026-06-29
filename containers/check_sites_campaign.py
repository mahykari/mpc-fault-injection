"""Drive the 8-combo disabled-Check()-sites campaign.

Each combo = a subset of {subprocessor_check, beaver_check, private_output_check}
passed as --disabled-sites to launch.py.  2 instances × 5k runs = 10k per combo,
reproducible via --seed 0.  Combos run serially; instances within a combo in
parallel (launch.py's default).
"""
from __future__ import annotations

import subprocess
import sys
from itertools import combinations
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SITES = ["subprocessor_check", "beaver_check", "private_output_check"]

combos: list[list[str]] = [[]]
for r in range(1, len(SITES) + 1):
  combos.extend(list(c) for c in combinations(SITES, r))


def run_combo(disabled: list[str], idx: int, total: int) -> None:
  label = ",".join(disabled) if disabled else "none"
  print(f"=== combo {idx}/{total}: disabled={label} ===", flush=True)
  cmd = [
    sys.executable,
    str(SCRIPT_DIR / "launch.py"),
    "--instances", "2",
    "--runs", "5000",
    "--seed", "0",
  ]
  if disabled:
    cmd += ["--disabled-sites", ",".join(disabled)]
  subprocess.run(cmd, check=True)
  print(f"--- done: disabled={label} ---", flush=True)


def main() -> None:
  total = len(combos)
  for idx, combo in enumerate(combos, 1):
    run_combo(combo, idx, total)
  print("=== campaign complete ===")


if __name__ == "__main__":
  main()
