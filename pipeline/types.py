"""Boundary types for the fault-injection pipeline.

Every component takes one of these in and produces one out.
mypy --strict enforces the contract; the pipeline itself is
the integration test (per BLUEPRINT.md invariants).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Protocol = Literal["mascot"]
VerdictLabel = Literal["pass", "bug", "inconclusive"]


@dataclass(frozen=True)
class Seed:
  value: int


@dataclass(frozen=True)
class CircilProgram:
  program_id: str
  source: str  # CircIL textual representation


@dataclass(frozen=True)
class MpspdzSource:
  program_id: str
  source: str  # MP-SPDZ Python DSL


@dataclass(frozen=True)
class MpspdzProgram:
  """Opaque handle to a compiled MP-SPDZ program.

  `ir_handle` will hold an MP-SPDZ `Compiler.program.Program` instance
  once the Compiler stub is replaced. Stub: None.
  """
  program_id: str
  ir_handle: object | None = None


@dataclass(frozen=True)
class InjectionRecord:
  gadget_kind: str          # one of: drift_and_restore | single_variable_bump | ...
  tape_index: int
  sync_lo_pc: int           # last sync-point PC before the gadget
  sync_hi_pc: int           # first sync-point PC after the gadget
  party_id: int
  details: str              # human-readable gadget parameters


@dataclass(frozen=True)
class MutatedProgram:
  original: MpspdzProgram
  mutated: MpspdzProgram
  record: InjectionRecord


@dataclass(frozen=True)
class PartyOutput:
  party_id: int
  stdout: str
  stderr: str
  exit_code: int


@dataclass(frozen=True)
class RunResult:
  program_id: str
  protocol: Protocol
  n_parties: int
  malicious_party: int
  honest_run: tuple[PartyOutput, ...]
  mutated_run: tuple[PartyOutput, ...]
  duration_ms: int
  timed_out: bool


@dataclass(frozen=True)
class Verdict:
  label: VerdictLabel
  reason: str
  honest_output: str
  actual_output: str


@dataclass(frozen=True)
class Report:
  program_id: str
  protocol: Protocol
  n_parties: int
  malicious_party: int
  fault: InjectionRecord
  verdict: Verdict
  duration_ms: int
