"""Fault Injector: produce honest + mutated IR pair.

Picks anchors centrally (LDSI sites on tape 0), then dispatches each
anchor to a `GadgetTemplate` to build a concrete splice. Multiple
gadgets per program is the default — `k` distinct anchors sampled
without replacement.

Adding a new gadget kind: add a file under `pipeline/gadgets/` and
register the template in the tuple in `pipeline/__init__.py`.

Compiling twice (once for honest, once for mutated) is the simple
substrate: MP-SPDZ's `Compiler.program.Program` resists deep-copy
because instruction objects have read-only descriptors, so we just
let the toolkit do two compiles from the same source and mutate one.
"""
from __future__ import annotations

import difflib
from random import Random
from typing import Any

from pipeline.config import NeedsInjector
from pipeline.gadgets import GadgetTemplate
from pipeline.mpspdz import MpSpdzCompilerToolkit, find_secret_writers, sync_signature
from pipeline.types import (
  InjectionRecord,
  MpspdzProgram,
  MpspdzSource,
  MutatedProgram,
)

TAPE_INDEX = 0
MAX_GADGETS = 5


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
    tape = mutated.tapes[TAPE_INDEX]
    anchors = find_secret_writers(tape)
    if not anchors:
      raise RuntimeError(f"no secret-writer anchors on tape {TAPE_INDEX}")

    k = rng.randint(1, min(MAX_GADGETS, len(anchors)))
    picks = rng.sample(anchors, k)
    gadgets = [
      rng.choice(self._templates).make(TAPE_INDEX, anchor, rng)
      for anchor in picks
    ]
    for gadget in gadgets:
      gadget.apply(mutated)

    self._check_sync_invariant(honest.program, mutated)
    record = InjectionRecord(
      tape_index=TAPE_INDEX,
      party_ids=tuple(self._config.malicious_parties),
      gadget_kinds=tuple(g.kind for g in gadgets),
      details=tuple(g.details for g in gadgets),
    )
    print(
      f"[injector] {len(gadgets)} gadget(s) on tape {record.tape_index} "
      f"(parties {list(record.party_ids)}):"
    )
    for kind, detail in zip(record.gadget_kinds, record.details):
      print(f"  - {kind}: {detail}")
    self._print_tape_diff(honest.program.tapes[TAPE_INDEX], mutated.tapes[TAPE_INDEX])
    return MutatedProgram(
      original=honest,
      mutated=MpspdzProgram(program=mutated),
      record=record,
    )

  @staticmethod
  def _print_tape_diff(honest_tape: Any, mutated_tape: Any) -> None:
    honest_lines = [str(i) for b in honest_tape.basicblocks for i in b.instructions]
    mutated_lines = [str(i) for b in mutated_tape.basicblocks for i in b.instructions]
    diff = difflib.unified_diff(
      honest_lines, mutated_lines,
      fromfile="honest", tofile="mutated", lineterm="", n=1,
    )
    print("[injector] tape diff:")
    for line in diff:
      print(f"  {line}")

  @staticmethod
  def _check_sync_invariant(honest: Any, mutated: Any) -> None:
    """Refuse to run if the mutation reshaped the inter-party message flow.

    Honest parties run unmutated bytecode and expect a specific sequence
    of network-touching ops; if the mutated tape's sequence diverges they
    would deadlock or interpret messages out of order.
    """
    for idx, (honest_tape, mutated_tape) in enumerate(
      zip(honest.tapes, mutated.tapes)
    ):
      honest_sig = sync_signature(honest_tape)
      mutated_sig = sync_signature(mutated_tape)
      if honest_sig != mutated_sig:
        raise RuntimeError(
          f"sync signature diverged on tape {idx}:\n"
          f"  honest:  {honest_sig}\n"
          f"  mutated: {mutated_sig}"
        )
