"""Campaign store: the work queue and the results table are one thing.

An experiment is a (config, seed) pair. Its request fields are written once at
campaign start and never change; its result fields stay NULL until a worker
reports back. "Pending work" is therefore not a separate queue, it is the set
of rows with no result yet, which is why killing the round barrier costs us no
new infrastructure.

Three tables, no JSON:

  config      One row per (protocol, n_parties, ...) grid point. Narrow, a
              dozen rows. A new knob is a new column here with a default on
              old rows; ordinary schema evolution, not churn tax.
  experiment  One row per run. Foreign key to config, plus seed, lease fields,
              and result fields. The fact table.
  injection   Child of experiment, one row per gadget spliced. `gadget_kinds`
              and `details` are tuples (types.InjectionRecord), so they are
              genuinely one-to-many and get a table, not a blob column.

Single writer by construction: only the dispatcher opens this file. Workers
reach it over HTTP and never touch sqlite, so there is no concurrent-writer
problem to solve here.

Data interaction only. Expanding the protocol x party-count grid and allocating
seeds belong to the campaign layer, which calls in here.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, cast

from pipeline.types import Protocol, Report

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
  id INTEGER PRIMARY KEY,
  protocol TEXT NOT NULL,
  n_parties INTEGER NOT NULL,
  corrupt_set TEXT NOT NULL,
  expression_depth INTEGER NOT NULL,
  combo TEXT NOT NULL,
  timeout_s REAL NOT NULL,
  UNIQUE (protocol, n_parties, corrupt_set, expression_depth, combo, timeout_s)
);

CREATE TABLE IF NOT EXISTS experiment (
  id INTEGER PRIMARY KEY,
  config_id INTEGER NOT NULL REFERENCES config(id),
  seed INTEGER NOT NULL UNIQUE,
  claimed_at TEXT,
  lease_expires_at TEXT,
  attempts INTEGER NOT NULL DEFAULT 0,
  completed_at TEXT,
  verdict TEXT,
  reason TEXT,
  wall_ms INTEGER,
  timed_out INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_experiment_available
  ON experiment(completed_at, claimed_at, id);
CREATE INDEX IF NOT EXISTS idx_experiment_exhausted
  ON experiment(completed_at, attempts, lease_expires_at);
CREATE INDEX IF NOT EXISTS idx_experiment_verdict ON experiment(verdict);

CREATE TABLE IF NOT EXISTS injection (
  id INTEGER PRIMARY KEY,
  experiment_id INTEGER NOT NULL REFERENCES experiment(id),
  ordinal INTEGER NOT NULL,
  tape_index INTEGER NOT NULL,
  gadget_kind TEXT NOT NULL,
  detail TEXT NOT NULL,
  UNIQUE (experiment_id, ordinal)
);
"""

# The config natural key, spelled once: it is both the UNIQUE tuple and the
# column list a claim reads back.
CONFIG_FIELDS = (
  "protocol, n_parties, corrupt_set, expression_depth, combo, timeout_s")

# A seed whose pipeline run raises leaves no report, so its lease expires and it
# is handed to the next worker, which fails the same deterministic way. Without
# a cap that row cycles forever and the campaign never drains.
MAX_ATTEMPTS = 3
ABANDONED = "abandoned"
ABANDONED_REASON = f"no report after {MAX_ATTEMPTS} attempts"


@dataclass(frozen=True)
class ExperimentConfig:
  """One grid point. Everything a worker needs to build a `Config`.

  `corrupt_set` is genuinely set-valued: the threat model samples a non-empty
  S subset of {0..n-1} with |S| <= t, so it is neither a count nor always
  `range(k)`. It is the one serialised container in the schema, stored as a
  sorted comma-separated party-id list.
  """
  protocol: Protocol
  n_parties: int
  corrupt_set: frozenset[int]
  expression_depth: int
  combo: str
  timeout_s: float

  @property
  def malicious_parties(self) -> list[int]:
    """`pipeline.Config.malicious_parties` is a list; hand it one."""
    return sorted(self.corrupt_set)


@dataclass(frozen=True)
class ClaimedExperiment:
  """A leased unit of work. `GET /next` serializes this to a worker."""
  experiment_id: int
  seed: int
  config: ExperimentConfig


class Store:
  """Owns the sqlite file. Instantiated once, in the dispatcher."""

  def __init__(self, path: Path) -> None:
    """Open (creating if absent) and apply the schema.

    Schema application must be idempotent: the dispatcher restarts and
    reattaches to a live campaign rather than starting a fresh one.
    """
    self.store_connection = sqlite3.connect(path)
    self.store_connection.execute("PRAGMA foreign_keys = ON")
    self.store_connection.executescript(SCHEMA)
    self.store_connection.commit()
    self.last_sweep: datetime | None = None

  def insert_config(self, config: ExperimentConfig) -> int:
    """Return this grid point's row id, inserting it if new.

    Idempotent through the natural-key UNIQUE: re-running campaign setup
    reattaches to the existing row instead of duplicating it.
    """
    key = (
      config.protocol, config.n_parties, _pack_corrupt_set(config.corrupt_set),
      config.expression_depth, config.combo, config.timeout_s,
    )
    self.store_connection.execute(
      f"INSERT OR IGNORE INTO config ({CONFIG_FIELDS}) VALUES (?, ?, ?, ?, ?, ?)",
      key)
    row = self.store_connection.execute(
      "SELECT id FROM config WHERE protocol = ? AND n_parties = ? "
      "AND corrupt_set = ? AND expression_depth = ? AND combo = ? "
      "AND timeout_s = ?",
      key).fetchone()
    self.store_connection.commit()
    return int(row[0])

  def insert_experiments(self, config_id: int, seeds: Iterable[int]) -> int:
    """Enqueue one experiment per seed; return how many rows were created.

    Idempotency is a schema property (seed is UNIQUE), not caller bookkeeping:
    replaying setup inserts nothing the second time and returns 0.
    """
    before = self.store_connection.total_changes
    self.store_connection.executemany(
      "INSERT OR IGNORE INTO experiment (config_id, seed) VALUES (?, ?)",
      ((config_id, seed) for seed in seeds))
    self.store_connection.commit()
    return self.store_connection.total_changes - before

  def claim(self, lease_s: float) -> ClaimedExperiment | None:
    """Lease the oldest available experiment, or None if the campaign is done.

    Available = no result yet AND (never claimed OR lease expired). Lease
    expiry is the crash-recovery story: a worker that dies mid-run leaves a row
    claimed but unreported, and after `lease_s` it returns to the queue. Set it
    well above the pipeline timeout (5x) so a slow-but-alive run is never
    handed to a second worker.

    None is load-bearing: it makes a worker exit, and the dispatcher turns it
    into a 204.

    A row is served at most `MAX_ATTEMPTS` times, so a seed that kills every
    worker it touches is retired rather than cycled forever.
    """
    now = datetime.now(timezone.utc)
    self._sweep_if_due(now, lease_s)
    # Select and lease in one statement: no window where the row is picked but
    # not yet leased.
    row = self.store_connection.execute(
      "UPDATE experiment SET claimed_at = ?, lease_expires_at = ?, "
      "attempts = attempts + 1 "
      "WHERE id = (SELECT id FROM experiment "
      "            WHERE completed_at IS NULL "
      "              AND (claimed_at IS NULL OR lease_expires_at < ?) "
      "              AND attempts < ? "
      "            ORDER BY id LIMIT 1) "
      "RETURNING id, seed, config_id",
      (_stamp(now), _stamp(now + timedelta(seconds=lease_s)),
       _stamp(now), MAX_ATTEMPTS)).fetchone()
    self.store_connection.commit()
    if row is None:
      return None
    return ClaimedExperiment(
      experiment_id=int(row[0]),
      seed=int(row[1]),
      config=self._config(int(row[2])),
    )

  def record(self, experiment_id: int, report: Report) -> None:
    """Write result fields and injection child rows; clear the lease.

    Idempotent on experiment_id: a worker may retry a POST after a transport
    failure, and that must not duplicate injection rows.
    """
    # `completed_at IS NULL` is the idempotency guard: a retried POST updates
    # nothing, so the child inserts are skipped too.
    # timed_out stays NULL: RunResult.timed_out dies in the Reporter and never
    # reaches the Report, so there is nothing here to write that isn't a guess
    # off the verdict text.
    completed = self.store_connection.execute(
      "UPDATE experiment SET completed_at = ?, claimed_at = NULL, "
      "lease_expires_at = NULL, verdict = ?, reason = ?, wall_ms = ? "
      "WHERE id = ? AND completed_at IS NULL",
      (_stamp(datetime.now(timezone.utc)), report.verdict.category,
       report.verdict.reason, report.duration_ms, experiment_id)).rowcount
    if completed:
      fault = report.fault
      self.store_connection.executemany(
        "INSERT INTO injection "
        "(experiment_id, ordinal, tape_index, gadget_kind, detail) "
        "VALUES (?, ?, ?, ?, ?)",
        ((experiment_id, ordinal, fault.tape_index, kind, detail)
         for ordinal, (kind, detail)
         in enumerate(zip(fault.gadget_kinds, fault.details))))
    self.store_connection.commit()

  def counts(self) -> dict[str, int]:
    """Verdict tallies over completed experiments, for progress reporting.

    Keys are VerdictCategory values. Replaces the per-round aggregate summary.
    """
    rows = self.store_connection.execute(
      "SELECT verdict, COUNT(*) FROM experiment "
      "WHERE completed_at IS NOT NULL GROUP BY verdict").fetchall()
    return {str(verdict): int(count) for verdict, count in rows}

  def _sweep_if_due(self, now: datetime, lease_s: float) -> None:
    """Rate-limit the sweep: it scans, and every claim would make that quadratic.

    A row cannot become abandonable faster than its own lease expires, so once
    per `lease_s` is as often as sweeping can possibly change an outcome. Riding
    it on every claim pinned the dispatcher at 97% CPU against a 2M-row table
    and starved every other request.
    """
    if (self.last_sweep is not None
        and (now - self.last_sweep).total_seconds() < lease_s):
      return
    self._abandon_exhausted(now)
    self.last_sweep = now

  def _abandon_exhausted(self, now: datetime) -> None:
    """Retire poison pills so they leave the pending set and show in `counts`.

    Only once the lease has expired: a row on its last attempt may still be
    running and about to report. Retiring it as a verdict rather than leaving
    it pending is what lets the campaign actually drain.
    """
    self.store_connection.execute(
      "UPDATE experiment SET completed_at = ?, claimed_at = NULL, "
      "lease_expires_at = NULL, verdict = ?, reason = ? "
      "WHERE completed_at IS NULL AND attempts >= ? AND lease_expires_at < ?",
      (_stamp(now), ABANDONED, ABANDONED_REASON, MAX_ATTEMPTS, _stamp(now)))

  def _config(self, config_id: int) -> ExperimentConfig:
    row = self.store_connection.execute(
      f"SELECT {CONFIG_FIELDS} FROM config WHERE id = ?",
      (config_id,)).fetchone()
    return ExperimentConfig(
      protocol=cast(Protocol, row[0]),
      n_parties=int(row[1]),
      corrupt_set=_unpack_corrupt_set(str(row[2])),
      expression_depth=int(row[3]),
      combo=str(row[4]),
      timeout_s=float(row[5]),
    )


def _pack_corrupt_set(parties: frozenset[int]) -> str:
  return ",".join(str(party) for party in sorted(parties))


def _unpack_corrupt_set(packed: str) -> frozenset[int]:
  return frozenset(int(party) for party in packed.split(",") if party)


def _stamp(moment: datetime) -> str:
  """ISO-8601 UTC, so lease expiry compares lexicographically in SQL."""
  return moment.isoformat()
