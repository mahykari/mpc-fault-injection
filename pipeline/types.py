"""Boundary types between pipeline components.

These carry content and results between stages. Identity (`program_id`,
`protocol`, party counts, corrupt set) lives on `Config`, not on
these dataclasses — see rule #3 in CLAUDE.md / memory.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Protocol = Literal["mascot", "semi"]
VerdictCategory = Literal["caught", "inert", "aborted", "honest_invalid", "bug"]


@dataclass(frozen=True)
class Seed:
  value: int


@dataclass(frozen=True)
class CircilProgram:
  """Wraps an in-memory `circil.ir.node.Circuit`.

  Typed `Any` because python-circil ships no type stubs. The
  Translator walks this AST to emit MP-SPDZ DSL source.
  """
  circuit: Any = field(repr=False)


@dataclass(frozen=True)
class MpspdzSource:
  source: str  # MP-SPDZ Python DSL


@dataclass(frozen=True)
class MpspdzProgram:
  """Wraps an in-memory MP-SPDZ `Compiler.program.Program`.

  Typed `Any` because MP-SPDZ ships no type stubs. Materialization to
  `.bc`/`.sch` happens in the Executor, via the toolkit's finalize.
  """
  program: Any = field(repr=False)


@dataclass(frozen=True)
class InjectionRecord:
  tape_index: int
  party_ids: tuple[int, ...]
  gadget_kinds: tuple[str, ...]
  details: tuple[str, ...]


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
  honest_run: tuple[PartyOutput, ...]
  mutated_run: tuple[PartyOutput, ...]
  duration_ms: int
  timed_out: bool


@dataclass(frozen=True)
class Verdict:
  category: VerdictCategory
  reason: str
  honest_output: str
  mutated_output: str


@dataclass(frozen=True)
class Report:
  fault: InjectionRecord
  verdict: Verdict
  duration_ms: int
