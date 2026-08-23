"""Source-layer injector: mutate the CircIL AST, then compile both twins.

The bytecode injector compiles once and rewrites instructions. This one
rewrites the circuit before translation, so honest and mutated are two
separate compiles of two separate sources. The diff is DSL text rather
than opcodes, which is legible.

`Config.mutation_kind` picks what the mutated twin gets. `inject`
introduces terms the match did not bind and is the fuzzer. `rearrange`
is semantics-preserving and is the control arm: a divergence under it
is a harness defect, not a finding.
"""
from __future__ import annotations

from typing import Any, Protocol as View

from pipeline.config import NeedsInjector
from pipeline.types import MutationKind
from pipeline.rewrite import rewrite_circuit
from pipeline.rewrite.inject import inject_circuit
from pipeline.types import (
  CircilProgram,
  InjectionRecord,
  MpspdzProgram,
  MutatedProgram,
)

MAX_REWRITES = 3

# Source-layer records carry no tape.
NO_TAPE = 0

class Mutation(View):
  """What both mutators return: a new circuit plus the rules that fired."""
  @property
  def circuit(self) -> Any: ...
  @property
  def rule_names(self) -> tuple[str, ...]: ...


class Mutator(View):
  def __call__(self, circuit: Any, seed: int, amount: int) -> Mutation: ...


_MUTATORS: dict[MutationKind, Mutator] = {
  "rearrange": rewrite_circuit,
  "inject": inject_circuit,
}


class SourceInjector:
  def __init__(self, toolkit: Any, compiler: Any, config: NeedsInjector) -> None:
    self._toolkit = toolkit
    self._compiler = compiler
    self._config = config

  def inject(self, circil: CircilProgram, honest: MpspdzProgram) -> MutatedProgram:
    from pipeline.translator import translate_to_mpspdz

    mutate = _MUTATORS[self._config.mutation_kind]
    result = mutate(
      circil.circuit, seed=self._config.seed.value, amount=MAX_REWRITES
    )
    mutated_source = translate_to_mpspdz(CircilProgram(circuit=result.circuit))
    mutated = self._compiler.compile(mutated_source)

    record = InjectionRecord(
      tape_index=NO_TAPE,
      party_ids=tuple(self._config.malicious_parties),
      gadget_kinds=result.rule_names,
      details=tuple("source rewrite: %s" % name for name in result.rule_names),
    )
    print(
      "[injector/source] %d rule(s) applied (parties %s):"
      % (len(result.rule_names), list(record.party_ids))
    )
    for name in result.rule_names:
      print("  - %s" % name)
    if not result.rule_names:
      print("  (no rule fired; twins are identical)")
    return MutatedProgram(original=honest, mutated=mutated, record=record)


