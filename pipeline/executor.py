"""Stub: MP-SPDZ Executor.

Real impl plan (per BLUEPRINT.md):
  1. Materialize original IR → runs/<id>/honest/Programs/Bytecode/*.bc
                              → runs/<id>/honest/Programs/Schedules/*.sch
  2. Materialize mutated IR  → runs/<id>/mutated/Programs/...
  3. Launch n × MP-SPDZ/bin/Linux-amd64/mascot-party.x twice
     (honest twin: all parties read from honest/;
      mutated twin: malicious_party reads from mutated/, others from honest/).
  4. Hard timeout (default 30s); collect each party's stdout/stderr/exit code.

Binary path: MP-SPDZ/bin/Linux-amd64/<protocol>-party.x (statically
linked, from the v0.4.2 binary distribution).

For now: pretend honest and mutated runs both produced "result: 3".
"""
from __future__ import annotations

import time

from pipeline.types import (
  MutatedProgram,
  PartyOutput,
  Protocol,
  RunResult,
)


def execute(
  mutated: MutatedProgram,
  protocol: Protocol,
  n_parties: int,
  malicious_party: int,
  timeout_s: float = 30.0,
) -> RunResult:
  program_id = mutated.original.program_id
  print(
    f"[executor] STUB: would launch {n_parties}× {protocol}-party.x for "
    f"{program_id} (twin-run, malicious party {malicious_party})"
  )
  print(
    f"[executor] STUB: would materialize honest+mutated to runs/<id>/"
  )
  start = time.monotonic()
  fake_out = "result: 3"
  honest = tuple(
    PartyOutput(party_id=i, stdout=fake_out, stderr="", exit_code=0)
    for i in range(n_parties)
  )
  mutated_run = tuple(
    PartyOutput(party_id=i, stdout=fake_out, stderr="", exit_code=0)
    for i in range(n_parties)
  )
  return RunResult(
    program_id=program_id,
    protocol=protocol,
    n_parties=n_parties,
    malicious_party=malicious_party,
    honest_run=honest,
    mutated_run=mutated_run,
    duration_ms=int((time.monotonic() - start) * 1000),
    timed_out=False,
  )
