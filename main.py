"""Pipeline entrypoint, for the host and inside a container.

Subcommands:
  run          Execute the fuzzing pipeline (default if no subcommand given)
  aggregate    Roll up runs/*/report.json into runs/results.db
  rerun-inert  Re-run inert cases under semi-honest to classify them

`uv run python main.py` runs (BLUEPRINT invariant). With no env it runs
seeds 0..N_RUNS-1 as instance 0 with DEFAULTS. The `CONFIG` env points at a
JSON run spec (written per-instance by the launcher) carrying everything:
  seeds        list of seeds this run executes      (default range(N_RUNS))
  instance_id  namespaces run artifacts             (default 0, env INSTANCE_ID)
  dispatcher   base URL to pull work from           (default none, env DISPATCHER)
  <other keys> Config-field overrides onto DEFAULTS (e.g. expression_depth)

With `dispatcher` set, seeds are ignored: the process becomes a worker that
pulls one experiment at a time and exits when the campaign drains. Containers
take that route and get both keys from the environment, no spec file.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from pipeline import Config
from pipeline.instance import run_dispatcher_instance, run_instance
from pipeline.config import apply_overrides
from pipeline.mpspdz import MpSpdzPartyBinary
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
  timeout_s=120.0,
  use_patched_binary=True,
  seeded_bug_binary=False,
)

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  seed INTEGER,
  protocol TEXT,
  n_parties INTEGER,
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


def _from_spec_or_env(spec: dict[str, Any], key: str, env: str) -> str | None:
  """Workers carry no spec file, so the launcher passes these as env."""
  value = spec.pop(key, None)
  return str(value) if value is not None else os.environ.get(env)


def cmd_run(_args: argparse.Namespace) -> None:
  spec = _spec()
  seeds = spec.pop("seeds", list(range(N_RUNS)))
  instance_id = int(_from_spec_or_env(spec, "instance_id", "INSTANCE_ID") or 0)
  dispatcher = _from_spec_or_env(spec, "dispatcher", "DISPATCHER")
  config = apply_overrides(DEFAULTS, spec)
  if dispatcher:
    run_dispatcher_instance(config, dispatcher, instance_id)
  else:
    run_instance(config, seeds, instance_id)


def cmd_aggregate(args: argparse.Namespace) -> None:
  conn = sqlite3.connect(DB_PATH)
  conn.executescript(DB_SCHEMA)
  # Backfill the column on a pre-protocol DB; CREATE IF NOT EXISTS won't add it.
  columns = {row[1] for row in conn.execute("PRAGMA table_info(runs)")}
  if "protocol" not in columns:
    conn.execute("ALTER TABLE runs ADD COLUMN protocol TEXT DEFAULT 'mascot'")
  if "n_parties" not in columns:
    conn.execute("ALTER TABLE runs ADD COLUMN n_parties INTEGER DEFAULT 3")
  # After the columns are guaranteed present, not before (fresh vs migrated DB).
  conn.execute("CREATE INDEX IF NOT EXISTS idx_protocol_verdict ON runs(protocol, verdict)")

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
    combo = data.get("combo", "baseline")
    protocol = data.get("protocol", "mascot")
    n_parties = data.get("n_parties", 3)

    conn.execute(
      "INSERT OR REPLACE INTO runs "
      "(id, seed, protocol, n_parties, combo, verdict, wall_ms, instance_id, retired_at) "
      "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
      (case_id, seed, protocol, n_parties, combo, verdict, wall_ms, instance_id),
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


def cmd_rerun_inert(args: argparse.Namespace) -> None:
  """Re-run inert mutations under semi-honest protocol to classify them.

  Inert under malicious = either truly inert (no semantic change) or
  active-but-masked (MAC checks caught the deviation). Re-running
  without MAC checks reveals which is which.
  """
  conn = sqlite3.connect(DB_PATH)
  cur = conn.execute(
    "SELECT id FROM runs WHERE verdict='inert' AND retired_at IS NULL"
  )
  inert_ids = [row[0] for row in cur.fetchall()]
  conn.close()

  if not inert_ids:
    print("no inert runs to rerun")
    return

  if args.limit:
    inert_ids = inert_ids[:args.limit]

  print(f"re-running {len(inert_ids)} inert case(s) under semi-party.x")

  active_but_masked = 0
  truly_inert = 0
  errors = 0

  for run_id in inert_ids:
    result = _rerun_as_semi(run_id)
    if result == "active":
      active_but_masked += 1
      print(f"  {run_id}: active-but-masked")
    elif result == "inert":
      truly_inert += 1
      print(f"  {run_id}: truly-inert")
    else:
      errors += 1
      print(f"  {run_id}: error ({result})")

  print()
  print(f"active-but-masked: {active_but_masked}")
  print(f"truly-inert: {truly_inert}")
  if errors:
    print(f"errors: {errors}")


def _rerun_as_semi(run_id: str) -> str:
  """Re-run a single case under semi-party.x, return classification."""
  run_dir = RUNS_ROOT / run_id
  report_path = run_dir / "report.json"

  if not report_path.exists():
    return "missing report.json"

  with open(report_path) as f:
    report = json.load(f)

  honest_output = report["verdict"]["honest_output"]
  party_ids: list[int] = report["fault"]["party_ids"]

  config = _semi_config_for(run_id, party_ids)
  binary = MpSpdzPartyBinary(config)

  honest_dir = run_dir / "honest"
  mutated_dir = run_dir / "mutated"

  corrupt = frozenset(party_ids)
  party_cwds = tuple(
    mutated_dir if i in corrupt else honest_dir
    for i in range(config.n_parties)
  )

  try:
    results = binary.run_parties(party_cwds)
  except Exception as e:
    return f"execution error: {e}"

  semi_output = "".join(p.stdout for p in results)

  if semi_output == honest_output:
    return "inert"
  else:
    return "active"


def _semi_config_for(run_id: str, party_ids: list[int]) -> Config:
  """Build a Config for semi-party.x rerun of an existing case."""
  m = ID_PATTERN.match(run_id)
  if not m:
    raise ValueError(f"invalid run_id: {run_id}")
  instance_id = int(m.group(1))
  seed = int(m.group(2))

  return dataclasses.replace(
    DEFAULTS,
    instance_id=instance_id,
    seed=Seed(value=seed),
    protocol="semi",
    malicious_parties=party_ids,
    use_patched_binary=False,
  )


def main() -> None:
  parser = argparse.ArgumentParser(description="MPC fault-injection pipeline")
  subs = parser.add_subparsers(dest="cmd")

  subs.add_parser("run", help="execute the fuzzing pipeline")

  subs.add_parser("aggregate", help="roll up reports into SQLite")

  rerun = subs.add_parser(
    "rerun-inert", help="re-run inert cases under semi-honest to classify them")
  rerun.add_argument(
    "--limit", type=int, default=0, help="max cases to rerun (0=all)")

  args = parser.parse_args()

  if args.cmd is None or args.cmd == "run":
    cmd_run(args)
  elif args.cmd == "aggregate":
    cmd_aggregate(args)
  elif args.cmd == "rerun-inert":
    cmd_rerun_inert(args)


if __name__ == "__main__":
  main()
