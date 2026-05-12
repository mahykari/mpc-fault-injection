"""single_variable_bump: shift one secret register by an immediate constant.

BLUEPRINT § "Scope: gadget insertion only" — the s ← s + c template.
Splices one ADDSI (local-only, no `Player::` calls) into the gap,
targeting the destination register of the first secret load on the
chosen tape.

Effect on MASCOT: the corrupt party's share of s shifts by c while its
MAC for s stays the same as in the honest run. When the protocol later
opens any value that depends on s, the MAC equation no longer balances
and the parties abort with `MacCheck Failure` at OPEN.
"""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Any

from pipeline.gadgets.types import Gadget, GadgetTemplate, SyncGap
from pipeline.mpspdz import (
  find_first_instruction,
  get_dst,
  insert_after,
  make_addsi,
  new_reg_like,
  set_dst,
)

KIND = "single_variable_bump"


@dataclass(frozen=True)
class SingleVariableBumpGadget:
  gap: SyncGap
  delta: int

  @property
  def kind(self) -> str:
    return KIND

  @property
  def details(self) -> str:
    return f"addsi r, r, +{self.delta} after first ldsi"

  def apply(self, program: Any) -> None:
    # MP-SPDZ uses SSA register allocation, so we can't bump in place
    # (`addsi r, r, δ` would write `r` twice). Instead, redirect the
    # LDSI to write a fresh register and let the bump's addsi write the
    # original register — preserving the single-writer invariant while
    # all downstream readers still see one definition of the original.
    tape = program.tapes[self.gap.tape_index]
    ldsi = find_first_instruction(tape, "ldsi")
    if ldsi is None:
      raise RuntimeError(f"no ldsi found on tape {self.gap.tape_index}")
    original_dst = get_dst(ldsi)
    fresh = new_reg_like(tape, original_dst)
    set_dst(ldsi, fresh)
    insert_after(tape, ldsi, make_addsi(dst=original_dst, src=fresh, imm=self.delta))


class SingleVariableBumpTemplate:
  """Applies wherever the gap contains a secret load to anchor on.

  Today: relies on the program-start gap convention and the assumption
  that there's an LDSI to find. A real `can_apply` will inspect the
  gap's instruction range once sync-point analysis lands.
  """

  @property
  def kind(self) -> str:
    return KIND

  def can_apply(self, gap: SyncGap) -> bool:
    return True

  def sample(self, gap: SyncGap, program: Any, rng: Random) -> Gadget:
    return SingleVariableBumpGadget(gap=gap, delta=rng.randint(1, 100))
