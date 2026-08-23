"""Unit 3: injections fire, stay well-typed, and source their operands.

The point of these checks is that an injection is *not* inert and *not*
synthesised: it must change the circuit, keep it typechecking, and take
its extra operand from a node already in scope.
"""
from __future__ import annotations

import contextlib
import io
from collections import Counter
from typing import Any

from tests.support import expect, generated

from pipeline.check import CircuitTypeError, check_circuit
from pipeline.rewrite.donors import donors_of_type, free_names, visible_names
from pipeline.rewrite.inject import INJECTIONS, inject_circuit
from pipeline.translator import translate_to_mpspdz
from pipeline.types import CircilProgram

BATCH = 40
INJECTIONS_PER_CIRCUIT = 2


def _statements(circuit: Any) -> list[str]:
  return [str(s) for s in circuit.statements]


def run() -> None:
  print("test_injection")

  with contextlib.redirect_stdout(io.StringIO()):
    circuits = [generated(seed) for seed in range(BATCH)]

  fired: Counter[str] = Counter()
  changed = 0
  broken: list[str] = []

  for seed, circuit in enumerate(circuits):
    before = _statements(circuit)
    result = inject_circuit(circuit, seed=seed, amount=INJECTIONS_PER_CIRCUIT)
    fired.update(result.rule_names)
    if _statements(result.circuit) != before:
      changed += 1
    try:
      check_circuit(result.circuit)
    except CircuitTypeError as failure:
      broken.append("seed %d: %s" % (seed, failure))
      continue
    with contextlib.redirect_stdout(io.StringIO()):
      translate_to_mpspdz(CircilProgram(circuit=result.circuit))

  for bad in broken[:3]:
    print("    " + bad)
  expect(not broken, "%d injected circuits typecheck and translate" % BATCH)
  expect(changed > BATCH // 2, "injections change the circuit (%d/%d)" % (changed, BATCH))
  for rule in INJECTIONS:
    expect(fired[rule.name] > 0, "%s fired (%d)" % (rule.name, fired[rule.name]))

  first = inject_circuit(circuits[0], seed=7, amount=INJECTIONS_PER_CIRCUIT)
  second = inject_circuit(circuits[0], seed=7, amount=INJECTIONS_PER_CIRCUIT)
  expect(
    first.rule_names == second.rule_names
    and _statements(first.circuit) == _statements(second.circuit),
    "same seed injects identically",
  )

  # Every donor a rule could pick must already be nameable at the splice.
  leaks = []
  for circuit in circuits[:12]:
    for index in range(len(circuit.statements)):
      scope = visible_names(circuit, index)
      for signal in circuit.inputs:
        for donor in donors_of_type(circuit, index, signal.type_hint):
          if not free_names(donor) <= scope:
            leaks.append(str(donor))
  expect(not leaks, "every donor is in scope at its splice point")
