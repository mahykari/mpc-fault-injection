"""Small-bump and sign-flip gadgets anchored on an LDSI.

Both templates use the same dst-redirection trick to stay SSA-safe:
the LDSI's destination register is routed through a fresh register,
and the gadget re-defines the original destination from that fresh
register. Locally:

- Bump: `r := fresh + δ`, δ ∈ {+1, -1}.
- SignFlip: `r := fresh * -1` ≡ `-r mod P`.
"""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Any

from pipeline.gadgets.types import Gadget
from pipeline.mpspdz import (
  get_dst,
  insert_after,
  make_addsi,
  make_mulsi,
  new_reg_like,
  set_dst,
)

KIND_BUMP = "variable_bump"
KIND_SIGNFLIP = "variable_signflip"


def _redirect_through_fresh(tape: Any, anchor: Any) -> tuple[Any, Any]:
  """Reroute `anchor`'s destination through a fresh register.

  Returns `(original_dst, fresh)`. The caller inserts an instruction
  that re-defines `original_dst` from `fresh` immediately after `anchor`.
  """
  original_dst = get_dst(anchor)
  fresh = new_reg_like(tape, original_dst)
  set_dst(anchor, fresh)
  return original_dst, fresh


@dataclass(frozen=True)
class BumpGadget:
  tape_index: int
  anchor: Any
  delta: int

  @property
  def kind(self) -> str:
    return KIND_BUMP

  @property
  def details(self) -> str:
    return f"addsi r, r, {self.delta:+d} after ldsi"

  def apply(self, program: Any) -> None:
    tape = program.tapes[self.tape_index]
    original_dst, fresh = _redirect_through_fresh(tape, self.anchor)
    insert_after(tape, self.anchor, make_addsi(dst=original_dst, src=fresh, imm=self.delta))


@dataclass(frozen=True)
class SignFlipGadget:
  tape_index: int
  anchor: Any

  @property
  def kind(self) -> str:
    return KIND_SIGNFLIP

  @property
  def details(self) -> str:
    return "mulsi r, r, -1 after ldsi (sign flip)"

  def apply(self, program: Any) -> None:
    tape = program.tapes[self.tape_index]
    original_dst, fresh = _redirect_through_fresh(tape, self.anchor)
    insert_after(tape, self.anchor, make_mulsi(dst=original_dst, src=fresh, imm=-1))


class BumpTemplate:
  @property
  def kind(self) -> str:
    return KIND_BUMP

  def make(self, tape_index: int, anchor: Any, rng: Random) -> Gadget:
    return BumpGadget(tape_index=tape_index, anchor=anchor, delta=rng.choice([+1, -1]))


class SignFlipTemplate:
  @property
  def kind(self) -> str:
    return KIND_SIGNFLIP

  def make(self, tape_index: int, anchor: Any, rng: Random) -> Gadget:
    return SignFlipGadget(tape_index=tape_index, anchor=anchor)


