"""Stub: Oracle.

Real impl: classify per blueprint decision table.
| Mutated run aborted? | Output matches honest twin? | Verdict      |
|---|---|---|
| Yes (mac_fail / consistency_check_fail) | N/A | pass         |
| No                                      | Yes | pass         |
| No                                      | No  | BUG          |
| Crashed / timed out / segfault          | N/A | inconclusive |
"""
from __future__ import annotations

from pipeline.types import RunResult, Verdict


def judge(result: RunResult) -> Verdict:
  print("[oracle] STUB: classify twin-run")
  honest_output = result.honest_run[0].stdout if result.honest_run else ""
  actual_output = result.mutated_run[0].stdout if result.mutated_run else ""
  return Verdict(
    label="pass",
    reason="STUB: no real comparison performed",
    honest_output=honest_output,
    actual_output=actual_output,
  )
