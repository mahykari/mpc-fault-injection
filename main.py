"""Pipeline entrypoint, for the host and inside a container.

Subcommands:
  run        Execute the fuzzing pipeline (default if no subcommand given)
  aggregate  Roll up runs/*/report.json into runs/results.db

`uv run python main.py` runs (BLUEPRINT invariant). With no env it runs
seeds 0..N_RUNS-1 as instance 0 with DEFAULTS. The `CONFIG` env points at a
JSON run spec (written per-instance by the launcher) carrying everything:
  seeds        list of seeds this run executes      (default range(N_RUNS))
  instance_id  namespaces run artifacts             (default 0)
  <other keys> Config-field overrides onto DEFAULTS (e.g. expression_depth)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from pipeline import Config
from pipeline.instance import run_instance
from pipeline.config import apply_overrides
from pipeline.types import Seed

REPO_ROOT = Path(__file__).resolve().parent
MPSPDZ_ROOT = REPO_ROOT / "MP-SPDZ"
RUNS_ROOT = REPO_ROOT / "runs"
DB_PATH = RUNS_ROOT / "results.db"

N_RUNS = 200

DEFAULTS = Config(
  mpspdz_root=MPSPDZ_ROOT,
  runs_root=RUNS_ROOT,
  seed=Seed(value=0),
  protocol="mascot",
  n_parties=3,
  malicious_parties=[0, 1],
  timeout_s=30.0,
  use_patched_binary=True,
  seeded_bug_binary=False,
)

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  seed INTEGER,
  combo TEXT,
  verdict TEXT,
  wall_ms INTEGER,
  instance_id INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  retired_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_combo_verdict ON runs(combo, verdict);
"""

ID_PATTERN = re.compile(r"i(\d+)-case-(\d+)")


def _spec() -> dict[str, Any]:
  path = os.environ.get("CONFIG")
  return json.loads(Path(path).read_text()) if path else {}


def cmd_run(_args: argparse.Namespace) -> None:
  spec = _spec()
  seeds = spec.pop("seeds", list(range(N_RUNS)))
  instance_id = spec.pop("instance_id", 0)
  run_instance(apply_overrides(DEFAULTS, spec), seeds, instance_id)


def cmd_aggregate(args: argparse.Namespace) -> None:
  conn = sqlite3.connect(DB_PATH)
  conn.executescript(DB_SCHEMA)

  live_ids: set[str] = set()
  inserted = 0
  skipped = 0
  by_verdict: dict[str, int] = {}

  for report_path in RUNS_ROOT.glob("*/report.json"):
    case_id = report_path.parent.name
    m = ID_PATTERN.match(case_id)
    if not m:
      skipped += 1
      continue

    instance_id, seed = int(m.group(1)), int(m.group(2))

    with open(report_path) as f:
      data = json.load(f)

    if "verdict" not in data:
      skipped += 1
      continue

    live_ids.add(case_id)
    verdict = data["verdict"]["category"]
    wall_ms = data["duration_ms"]

    conn.execute(
      "INSERT OR REPLACE INTO runs "
      "(id, seed, combo, verdict, wall_ms, instance_id, retired_at) "
      "VALUES (?, ?, ?, ?, ?, ?, NULL)",
      (case_id, seed, args.combo, verdict, wall_ms, instance_id),
    )

    inserted += 1
    by_verdict[verdict] = by_verdict.get(verdict, 0) + 1

  if live_ids:
    placeholders = ",".join("?" * len(live_ids))
    cur = conn.execute(
      f"UPDATE runs SET retired_at = CURRENT_TIMESTAMP "
      f"WHERE id NOT IN ({placeholders}) AND retired_at IS NULL",
      tuple(live_ids),
    )
    retired = cur.rowcount
  else:
    retired = 0

  conn.commit()
  conn.close()

  print(f"inserted={inserted} skipped={skipped} retired={retired}")
  for v, n in sorted(by_verdict.items()):
    print(f"  {v}: {n}")


def main() -> None:
  parser = argparse.ArgumentParser(description="MPC fault-injection pipeline")
  subs = parser.add_subparsers(dest="cmd")

  subs.add_parser("run", help="execute the fuzzing pipeline")

  agg = subs.add_parser("aggregate", help="roll up reports into SQLite")
  agg.add_argument("--combo", default="", help="disabled-sites combo label")

  args = parser.parse_args()

  if args.cmd is None or args.cmd == "run":
    cmd_run(args)
  elif args.cmd == "aggregate":
    cmd_aggregate(args)


if __name__ == "__main__":
  main()
