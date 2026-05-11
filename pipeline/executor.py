"""Executor: launch the honest and mutated twins.

Honest twin: every party reads from `honest/`.
Mutated twin: the corrupt party reads from `mutated/`; others read
from `honest/`. Per-party cwd lists are derived on `Config`.

For the plumbing milestone the Injector is a passthrough, so
`mutated/Programs/` is a byte-for-byte mirror of `honest/Programs/`.
The mirror step goes away when the Injector emits its own bytecode.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from pipeline.config import NeedsExecutor
from pipeline.mpspdz import MpSpdzPartyBinary, TwinRunPlan
from pipeline.timing import Timer
from pipeline.types import MutatedProgram, RunResult


class Executor:
  def __init__(
    self, party_binary: MpSpdzPartyBinary, config: NeedsExecutor,
  ) -> None:
    self._party_binary = party_binary
    self._config = config

  def execute(self, mutated: MutatedProgram) -> RunResult:
    print(
      f"[executor] {self._config.program_id}: twin-run "
      f"(gadget={mutated.record.gadget_kind}, "
      f"corrupt party={mutated.record.party_id})"
    )
    self._mirror_honest_to_mutated()
    with Timer() as timer:
      honest = self._party_binary.run_parties(
        self._plan_for(self._config.honest_party_cwds),
      )
      perturbed = self._party_binary.run_parties(
        self._plan_for(self._config.mutated_party_cwds),
      )
    return RunResult(
      honest_run=honest,
      mutated_run=perturbed,
      duration_ms=timer.elapsed_ms,
      timed_out=any(p.exit_code == -1 for p in honest + perturbed),
    )

  def _plan_for(self, party_cwds: tuple[Path, ...]) -> TwinRunPlan:
    return TwinRunPlan(
      program_id=self._config.program_id,
      party_cwds=party_cwds,
      timeout_s=self._config.timeout_s,
    )

  def _mirror_honest_to_mutated(self) -> None:
    src = self._config.honest_dir / "Programs"
    dst = self._config.mutated_dir / "Programs"
    for sub in ("Bytecode", "Schedules"):
      (dst / sub).mkdir(parents=True, exist_ok=True)
      for path in (src / sub).iterdir():
        shutil.copy2(path, dst / sub / path.name)
