"""Run one instance: a set of seeds through the pipeline, summarised.

The puppeteer (launch.py) spawns instances; each instance runs this loop
over its own seed slice. `instance_id` feeds `Config.program_id` so
artifacts from parallel instances don't collide under a shared `runs/`.
The Reporter persists each run; here we print one line per run plus a
closing summary, and suppress per-run pipeline output.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import typing
from typing import Iterable

from pipeline import Config, run_pipeline
from pipeline.timing import Timer
from pipeline.types import Report, Seed, VerdictCategory

_MAX_TIMEOUT_RETRIES = 2


def _timed_run(config: Config) -> tuple[Report, int]:
  with Timer() as timer:
    report = run_pipeline(config)
  return report, timer.elapsed_ms


def _run_with_retry(config: Config) -> tuple[Report, int]:
  report, total_ms = _timed_run(config)
  for _ in range(_MAX_TIMEOUT_RETRIES):
    if report.verdict.category != "aborted":
      break
    report, elapsed_ms = _timed_run(config)
    total_ms += elapsed_ms
  return report, total_ms


def run_instance(
  base_config: Config,
  seeds: Iterable[int],
  instance_id: int = 0,
) -> None:
  seeds = list(seeds)
  counts = {c: 0 for c in typing.get_args(VerdictCategory)}
  counts["error"] = 0
  bug_seeds: list[int] = []
  wall_ms: list[int] = []

  for seed in seeds:
    config = dataclasses.replace(
      base_config, seed=Seed(value=seed), instance_id=instance_id)
    sink = io.StringIO()
    try:
      with contextlib.redirect_stdout(sink):
        report, elapsed_ms = _run_with_retry(config)
    except Exception as exc:
      counts["error"] += 1
      print(f"[i{instance_id:02d} seed={seed:04d}] ERROR — {exc!s}")
      continue
    wall_ms.append(elapsed_ms)
    category = report.verdict.category
    counts[category] += 1
    if category == "bug":
      bug_seeds.append(seed)
    print(
      f"[i{instance_id:02d} seed={seed:04d}] "
      f"{category} — {report.verdict.reason} "
      f"({elapsed_ms} ms)")

  _print_summary(instance_id, len(seeds), counts, bug_seeds, wall_ms)


def _print_summary(
  instance_id: int,
  n_runs: int,
  counts: dict[str, int],
  bug_seeds: list[int],
  wall_ms: list[int],
) -> None:
  print()
  print(f"=== instance {instance_id:02d} summary ({n_runs} runs) ===")
  for category, count in counts.items():
    print(f"  {category:14s}: {count}")
  if bug_seeds:
    print(f"  bug seeds     : {bug_seeds}")
  if wall_ms:
    total_s = sum(wall_ms) / 1000
    mean_ms = sum(wall_ms) / len(wall_ms)
    print(f"  wall          : {total_s:.1f}s total, {mean_ms:.0f} ms/run mean")
