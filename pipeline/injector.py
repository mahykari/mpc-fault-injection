"""Fault Injector: produce honest + mutated IR pair.

A dispatcher over `GadgetTemplate`s. Per-mutation logic — what the
mutation looks like and where it lives in the IR — belongs in the
template, not here. Adding a new gadget kind is adding a file under
`pipeline/gadgets/` and registering it in the templates tuple in
`pipeline/__init__.py`.

Compiling twice (once for honest, once for mutated) is the simple
substrate: MP-SPDZ's `Compiler.program.Program` resists deep-copy
because instruction objects have read-only descriptors, so we just
let the toolkit do two compiles from the same source and mutate one.
"""
from __future__ import annotations

from random import Random
from typing import Any

from pipeline.config import NeedsInjector
from pipeline.gadgets import GadgetTemplate, SyncGap
from pipeline.mpspdz import MpSpdzCompilerToolkit
from pipeline.types import (
  InjectionRecord,
  MpspdzProgram,
  MpspdzSource,
  MutatedProgram,
)


class Injector:
  def __init__(
    self,
    toolkit: MpSpdzCompilerToolkit,
    templates: tuple[GadgetTemplate, ...],
    config: NeedsInjector,
  ) -> None:
    self._toolkit = toolkit
    self._templates = templates
    self._config = config

  def inject(
    self, source: MpspdzSource, honest: MpspdzProgram,
  ) -> MutatedProgram:
    mutated = self._toolkit.compile(self._config.program_id, source.source)
    rng = Random(self._config.seed.value)
    gap = self._pick_gap(mutated)
    template = self._pick_template(gap, rng)
    gadget = template.sample(gap, mutated, rng)
    gadget.apply(mutated)
    record = InjectionRecord(
      gadget_kind=gadget.kind,
      tape_index=gadget.gap.tape_index,
      sync_lo_pc=gadget.gap.lo_pc,
      sync_hi_pc=gadget.gap.hi_pc,
      party_id=self._config.malicious_party,
      details=gadget.details,
    )
    print(
      f"[injector] {record.gadget_kind} on tape {record.tape_index} "
      f"(party {record.party_id}): {record.details}"
    )
    return MutatedProgram(
      original=honest,
      mutated=MpspdzProgram(program=mutated),
      record=record,
    )

  @staticmethod
  def _pick_gap(program: Any) -> SyncGap:
    # Real sync-point analysis comes when the second template needs it.
    # For now: program-start gap on tape 0.
    return SyncGap(tape_index=0, lo_pc=0, hi_pc=0)

  def _pick_template(self, gap: SyncGap, rng: Random) -> GadgetTemplate:
    applicable = tuple(t for t in self._templates if t.can_apply(gap))
    if not applicable:
      raise RuntimeError(f"no gadget template applies to {gap}")
    return rng.choice(applicable)
