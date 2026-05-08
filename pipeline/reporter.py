"""Stub: Reporter.

Real impl: write structured JSON record to runs/<id>/report.json,
append to runs/bugs.jsonl on BUG verdict, runs/passes.jsonl otherwise.
For now: assemble Report dataclass from upstream data.
"""
from __future__ import annotations

from pipeline.types import MutatedProgram, Report, RunResult, Verdict


def report(
  mutated: MutatedProgram,
  run: RunResult,
  verdict: Verdict,
) -> Report:
  print(f"[reporter] STUB: would persist run record for {run.program_id}")
  return Report(
    program_id=run.program_id,
    protocol=run.protocol,
    n_parties=run.n_parties,
    malicious_party=run.malicious_party,
    fault=mutated.record,
    verdict=verdict,
    duration_ms=run.duration_ms,
  )
