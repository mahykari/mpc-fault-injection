"""Stub: Reporter.

Real impl: write structured JSON record to `config.report_path`,
append to runs/bugs.jsonl on BUG verdict, runs/passes.jsonl otherwise.
For now: assemble Report dataclass from upstream data.
"""
from __future__ import annotations

from pipeline.config import NeedsReporter
from pipeline.types import MutatedProgram, Report, RunResult, Verdict

import dataclasses
import json

def report(
  mutated: MutatedProgram,
  run: RunResult,
  verdict: Verdict,
  config: NeedsReporter,
) -> Report:
  result = Report(
    fault=mutated.record,
    verdict=verdict,
    duration_ms=run.duration_ms,
    combo=config.combo,
  )
  with open(config.report_path, "w") as f:
    json.dump(dataclasses.asdict(result), f, indent=2)
  return result
