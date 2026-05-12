"""immediate_swap: change the immediate operand of the first `ldsi` on a tape.

Not a BLUEPRINT-shape gadget (it mutates an existing instruction rather
than splicing a local-only block between sync points), but kept as the
first template because it's how the IR-mutation plumbing was proven and
it provides a useful smoke-test mutation that's caught by MASCOT's MAC
check at OPEN.
"""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Any

from pipeline.gadgets.types import Gadget, GadgetTemplate, SyncGap


KIND = "immediate_swap"


@dataclass(frozen=True)
class ImmediateSwapGadget:
  gap: SyncGap
  new_immediate: int

  @property
  def kind(self) -> str:
    return KIND

  @property
  def details(self) -> str:
    return f"ldsi immediate → {self.new_immediate}"

  def apply(self, program: Any) -> None:
    tape = program.tapes[self.gap.tape_index]
    for instruction in tape.basicblocks[0].instructions:
      if type(instruction).__name__ == "ldsi":
        instruction.args[1] = self.new_immediate
        return
    raise RuntimeError(
      f"no ldsi instruction found on tape {self.gap.tape_index}"
    )


class ImmediateSwapTemplate:
  """Always applies; produces a gadget that overwrites the first LDSI."""

  @property
  def kind(self) -> str:
    return KIND

  def can_apply(self, gap: SyncGap) -> bool:
    return True

  def sample(self, gap: SyncGap, program: Any, rng: Random) -> Gadget:
    return ImmediateSwapGadget(gap=gap, new_immediate=42)
