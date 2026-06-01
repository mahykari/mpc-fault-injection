"""Pipeline entrypoint: fuzz loop over N seeds, summarize verdicts.

Per-run output of the pipeline components is suppressed; this script
only prints one line per run plus a final summary.

`uv run python main.py` must always succeed (BLUEPRINT invariant).
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import typing
from pathlib import Path

from pipeline import Config, run_pipeline
from pipeline.types import Seed, VerdictCategory

REPO_ROOT = Path(__file__).resolve().parent
MPSPDZ_ROOT = REPO_ROOT / "MP-SPDZ"
RUNS_ROOT = REPO_ROOT / "runs"

N_RUNS = 200

BASE_CONFIG = Config(
  mpspdz_root=MPSPDZ_ROOT,
  runs_root=RUNS_ROOT,
  seed=Seed(value=0),
  protocol="mascot",
  n_parties=3,
  malicious_parties=(0, 1),
  timeout_s=30.0,
  use_patched_binary=True,
  seeded_bug_binary=False,
)


def main() -> None:
  counts: dict[str, int] = {c: 0 for c in typing.get_args(VerdictCategory)}
  counts["error"] = 0
  bugs: list[int] = []
  errors: list[tuple[int, str]] = []

  for seed in range(N_RUNS):
    config = dataclasses.replace(BASE_CONFIG, seed=Seed(value=seed))
    # Silence per-run pipeline prints (generator/translator/injector/...) so
    # only this loop's one-line-per-run summary reaches the terminal.
    # Subprocess stdout/stderr is unaffected — already collected via Popen.PIPE.
    sink = io.StringIO()
    try:
      with contextlib.redirect_stdout(sink):
        report = run_pipeline(config)
    except Exception as exc:
      counts["error"] += 1
      errors.append((seed, repr(exc)))
      print(f"[seed={seed:04d}] ERROR — {exc!s}")
      continue

    category = report.verdict.category
    counts[category] += 1
    if category == "bug":
      bugs.append(seed)
    print(f"[seed={seed:04d}] {category} — {report.verdict.reason}")

  print()
  print(f"=== Summary ({N_RUNS} runs) ===")
  for k, v in counts.items():
    print(f"  {k:14s}: {v}")
  if bugs:
    print(f"  bug seeds     : {bugs}")
  if errors:
    print(f"  error sample  : {errors[:5]}")


if __name__ == "__main__":
  main()
