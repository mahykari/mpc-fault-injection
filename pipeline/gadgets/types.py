"""Gadget framework.

A `GadgetTemplate` is a generation rule (kind + applicability + sampler).
A `Gadget` is a single fully-sampled instance that knows how to install
itself into an MP-SPDZ `Compiler.program.Program`. The Injector is a
dispatcher over a tuple of templates; per-template generation logic
lives in the template's own module.

This separation is what lets us add new gadget kinds without touching
the Injector — see BLUEPRINT.md § "Scope: gadget insertion only" for
the catalog of templates we're heading toward.
"""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Any, Protocol as View


@dataclass(frozen=True)
class SyncGap:
  """A spliceable region of one tape, between two consecutive sync points.

  Today these are constructed as a program-start stub (`tape_index=0,
  lo_pc=0, hi_pc=0`) — real sync-point analysis comes when the second
  template arrives and needs it. Eventually this will also carry live
  register sets so templates can sample over valid operands.
  """
  tape_index: int
  lo_pc: int
  hi_pc: int


class Gadget(View):
  """One fully-sampled gadget, ready to be installed."""

  @property
  def kind(self) -> str: ...

  @property
  def gap(self) -> SyncGap: ...

  @property
  def details(self) -> str:
    """Human-readable description of the mutation, for InjectionRecord."""
    ...

  def apply(self, program: Any) -> None:
    """Install this gadget into `program`. Mutates in place.

    The contract is `apply()` produces only side effects consistent
    with BLUEPRINT's local-only opcode whitelist — no `Player::` calls,
    so honest parties see no extra network traffic. The whitelist is
    enforced per template (today by construction, not by the type
    system).
    """
    ...


class GadgetTemplate(View):
  """A generation rule. Knows when it applies and how to sample."""

  @property
  def kind(self) -> str: ...

  def can_apply(self, gap: SyncGap) -> bool: ...

  def sample(self, gap: SyncGap, program: Any, rng: Random) -> Gadget:
    """Draw a concrete `Gadget` for the given gap from this template.

    `program` is passed so templates can peek at instructions inside
    `gap` (e.g. find the LDSI to anchor on) — required until SyncGap
    carries enough structural info on its own.
    """
    ...
