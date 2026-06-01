"""Executor: materialize the twin IRs to disk and launch both runs.

Honest twin: every party reads from `honest/`.
Mutated twin: the corrupt party reads from `mutated/`; others read
from `honest/`. Per-party cwd lists live on `Config`.
"""
from __future__ import annotations

from pipeline.config import NeedsExecutor
from pipeline.mpspdz import MpSpdzCompilerToolkit, MpSpdzPartyBinary
from pipeline.timing import Timer
from pipeline.types import MutatedProgram, RunResult


class Executor:
  def __init__(
    self,
    toolkit: MpSpdzCompilerToolkit,
    party_binary: MpSpdzPartyBinary,
    config: NeedsExecutor,
  ) -> None:
    self._toolkit = toolkit
    self._party_binary = party_binary
    self._config = config

  def execute(self, mutated: MutatedProgram) -> RunResult:
    print(
      f"[executor] {self._config.program_id}: twin-run "
      f"({len(mutated.record.gadget_kinds)} gadget(s), "
      f"corrupt parties={list(mutated.record.party_ids)})"
    )
    self._toolkit.finalize_into(mutated.original.program, self._config.honest_dir)
    self._toolkit.finalize_into(mutated.mutated.program, self._config.mutated_dir)
    with Timer() as timer:
      honest_run = self._party_binary.run_parties(
        self._config.program_id,
        self._config.honest_party_cwds,
        self._config.timeout_s,
      )
      mutated_run = self._party_binary.run_parties(
        self._config.program_id,
        self._config.mutated_party_cwds,
        self._config.timeout_s,
      )
    return RunResult(
      honest_run=honest_run,
      mutated_run=mutated_run,
      duration_ms=timer.elapsed_ms,
      timed_out=any(p.exit_code == -1 for p in honest_run + mutated_run),
    )
