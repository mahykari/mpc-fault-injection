"""Run one instance: pipeline cases, summarised.

Two loops share the per-case body:

  run_instance             walks a fixed seed slice. The pre-dispatcher model,
                           still what `uv run python main.py` does with no env.
  run_dispatcher_instance  pulls one experiment at a time from the dispatcher
                           and stops only when the campaign drains, so a slow
                           grid point can no longer leave other workers idle
                           at a round barrier.

`instance_id` feeds `Config.program_id` so artifacts from parallel workers
don't collide under a shared `runs/`. The Reporter persists each run; here we
print one line per run plus a closing summary, and suppress per-run pipeline
output.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import time
import typing
import urllib.error
import urllib.request
from functools import partial
from http import HTTPStatus
from http.client import HTTPException
from typing import Callable, Iterable, TypeVar

from pipeline import Config, run_pipeline
from pipeline.store import ClaimedExperiment
from pipeline.timing import Timer
from pipeline.types import Report, Seed, VerdictCategory
from pipeline.wire import claimed_from_payload, report_to_payload

_MAX_TIMEOUT_RETRIES = 2

_NEXT_ROUTE = "/next"
_RESULT_ROUTE = "/result"
_HTTP_TIMEOUT_S = 30.0
_BACKOFF_START_S = 1.0
_BACKOFF_MAX_S = 30.0

_T = TypeVar("_T")


def _empty_counts() -> dict[str, int]:
  counts = {c: 0 for c in typing.get_args(VerdictCategory)}
  counts["error"] = 0
  return counts


@dataclasses.dataclass
class _Tally:
  """Running verdict counts for one instance, printed once at the end."""
  counts: dict[str, int] = dataclasses.field(default_factory=_empty_counts)
  bug_seeds: list[int] = dataclasses.field(default_factory=list)
  wall_ms: list[int] = dataclasses.field(default_factory=list)

  def record(self, seed: int, report: Report, elapsed_ms: int) -> None:
    self.wall_ms.append(elapsed_ms)
    self.counts[report.verdict.category] += 1
    if report.verdict.category == "bug":
      self.bug_seeds.append(seed)

  def record_error(self) -> None:
    self.counts["error"] += 1


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


def _run_one(config: Config, tally: _Tally) -> Report | None:
  """One case: run it, tally it, print its line. None means it raised."""
  seed = config.seed.value
  sink = io.StringIO()
  try:
    with contextlib.redirect_stdout(sink):
      report, elapsed_ms = _run_with_retry(config)
  except Exception as exc:
    tally.record_error()
    print(f"[i{config.instance_id:02d} seed={seed:04d}] ERROR — {exc!s}")
    return None
  tally.record(seed, report, elapsed_ms)
  print(
    f"[i{config.instance_id:02d} seed={seed:04d}] "
    f"{report.verdict.category} — {report.verdict.reason} "
    f"({elapsed_ms} ms)")
  return report


def run_instance(
  base_config: Config,
  seeds: Iterable[int],
  instance_id: int = 0,
) -> None:
  seeds = list(seeds)
  tally = _Tally()

  for seed in seeds:
    config = dataclasses.replace(
      base_config, seed=Seed(value=seed), instance_id=instance_id)
    _run_one(config, tally)

  _print_summary(instance_id, len(seeds), tally)


def run_dispatcher_instance(
  base_config: Config,
  dispatcher: str,
  instance_id: int = 0,
) -> None:
  """Pull, run, report; until the dispatcher says the campaign is drained."""
  tally = _Tally()
  n_runs = 0
  print(f"[i{instance_id:02d}] pulling work from {dispatcher}")

  while True:
    claimed = _retrying(partial(_claim, dispatcher), "GET /next")
    if claimed is None:
      break
    n_runs += 1
    report = _run_one(_config_for(base_config, claimed, instance_id), tally)
    # A case that raised has no report to send, so its lease expires and the
    # dispatcher hands it to someone else.
    if report is not None:
      _retrying(
        partial(_send_result, dispatcher, claimed.experiment_id, report),
        "POST /result")

  _print_summary(instance_id, n_runs, tally)


def _config_for(
  base: Config,
  claimed: ClaimedExperiment,
  instance_id: int,
) -> Config:
  """Each item carries its own grid point, so the Config is per-run now."""
  item = claimed.config
  return dataclasses.replace(
    base,
    seed=Seed(value=claimed.seed),
    instance_id=instance_id,
    protocol=item.protocol,
    n_parties=item.n_parties,
    malicious_parties=list(item.malicious_parties),
    expression_depth=item.expression_depth,
    combo=item.combo,
    timeout_s=item.timeout_s,
  )


def _endpoint(dispatcher: str, route: str) -> str:
  return dispatcher.rstrip("/") + route


def _retrying(operation: Callable[[], _T], what: str) -> _T:
  """Ride out a dispatcher that is booting, restarting, or briefly wedged.

  Only transport failure lands here; a drained campaign is a 204, which is a
  successful response. Retry forever rather than die: a dead worker is a slot
  lost for the rest of the campaign.
  """
  delay = _BACKOFF_START_S
  while True:
    try:
      return operation()
    except (OSError, HTTPException) as exc:
      print(f"[dispatcher] {what} failed ({exc!s}); retry in {delay:.0f}s")
      time.sleep(delay)
      delay = min(delay * 2, _BACKOFF_MAX_S)


def _claim(dispatcher: str) -> ClaimedExperiment | None:
  """None is 204: no work left, ever. Transport failure raises instead."""
  request = urllib.request.Request(_endpoint(dispatcher, _NEXT_ROUTE))
  with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT_S) as response:
    if response.status == HTTPStatus.NO_CONTENT:
      return None
    return claimed_from_payload(json.load(response))


def _send_result(dispatcher: str, experiment_id: int, report: Report) -> None:
  """The store keys results by experiment_id, so a resent report is free."""
  body = json.dumps({
    "experiment_id": experiment_id,
    "report": report_to_payload(report),
  }).encode()
  request = urllib.request.Request(
    _endpoint(dispatcher, _RESULT_ROUTE),
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST")
  with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT_S):
    pass


def _print_summary(instance_id: int, n_runs: int, tally: _Tally) -> None:
  print()
  print(f"=== instance {instance_id:02d} summary ({n_runs} runs) ===")
  for category, count in tally.counts.items():
    print(f"  {category:14s}: {count}")
  if tally.bug_seeds:
    print(f"  bug seeds     : {tally.bug_seeds}")
  if tally.wall_ms:
    total_s = sum(tally.wall_ms) / 1000
    mean_ms = sum(tally.wall_ms) / len(tally.wall_ms)
    print(f"  wall          : {total_s:.1f}s total, {mean_ms:.0f} ms/run mean")
