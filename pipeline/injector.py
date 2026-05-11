"""Fault Injector: produce honest + mutated IR pair.

For the integration milestone the mutation is hardcoded — change the
immediate operand of the first `ldsi` (the secret-constant load for
`a` in the tutorial program) on tape 0. Static analysis to pick the
gap/gadget per BLUEPRINT comes later; right now this proves that
mutating the in-memory IR survives finalize and reaches the binary.

Compiling twice (once for honest, once for mutated) is the simple
substrate: MP-SPDZ's `Compiler.program.Program` resists deep-copy
because instruction objects have read-only descriptors, so we just
let the toolkit do two compiles from the same source and mutate one.
"""
from __future__ import annotations

from typing import Any

from pipeline.config import NeedsInjector
from pipeline.mpspdz import MpSpdzCompilerToolkit
from pipeline.types import (
  InjectionRecord,
  MpspdzProgram,
  MpspdzSource,
  MutatedProgram,
)

MUTATED_IMMEDIATE = 42


class Injector:
  def __init__(
    self, toolkit: MpSpdzCompilerToolkit, config: NeedsInjector,
  ) -> None:
    self._toolkit = toolkit
    self._config = config

  def inject(
    self, source: MpspdzSource, honest: MpspdzProgram,
  ) -> MutatedProgram:
    mutated_program = self._toolkit.compile(self._config.program_id, source.source)
    original_immediate = self._mutate_first_ldsi(mutated_program)
    record = InjectionRecord(
      gadget_kind="immediate_swap",
      tape_index=0,
      sync_lo_pc=0,
      sync_hi_pc=0,
      party_id=self._config.malicious_party,
      details=f"ldsi immediate {original_immediate} → {MUTATED_IMMEDIATE}",
    )
    print(f"[injector] {record.gadget_kind} on tape 0 (party {record.party_id}): {record.details}")
    return MutatedProgram(
      original=honest,
      mutated=MpspdzProgram(program=mutated_program),
      record=record,
    )

  @staticmethod
  def _mutate_first_ldsi(program: Any) -> int:
    """Change the immediate of the first `ldsi` on tape 0. Return the prior value."""
    for instruction in program.tapes[0].basicblocks[0].instructions:
      if type(instruction).__name__ == "ldsi":
        previous = instruction.args[1]
        instruction.args[1] = MUTATED_IMMEDIATE
        return int(previous)
    raise RuntimeError("no ldsi instruction found on tape 0")
