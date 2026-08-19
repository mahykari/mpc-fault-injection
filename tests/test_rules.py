"""Unit 2: rearrangements fire on real output, preserve typing, and repeat.

Deliberately measured against generated circuits rather than hand-built
ones: a hand-built call carries no template arguments, so a rule that
matched only those would be passing on input the generator never emits.
"""
from __future__ import annotations

import contextlib
import io
from typing import Any

from tests.support import expect, generated

from pipeline.check import CircuitTypeError, check_circuit
from pipeline.rewrite import REARRANGEMENTS, rewrite_circuit

BATCH = 120
REPEAT_SEEDS = (0, 1, 7, 11, 42)
REWRITES_PER_CIRCUIT = 3


def _fingerprint(circuit: Any) -> list[str]:
  return (
    [str(i) for i in circuit.inputs]
    + [str(o) for o in circuit.outputs]
    + [str(s) for s in circuit.statements]
  )


def _typechecks(circuit: Any) -> bool:
  try:
    check_circuit(circuit)
  except CircuitTypeError:
    return False
  return True


def _count_sites(rule: Any, node: Any, seen: list[int]) -> None:
  if rule.match(node) is not None:
    seen[0] += 1
  for attr in ("arguments", "statements", "template_arguments"):
    for child in getattr(node, attr, []) or []:
      _count_sites(rule, child, seen)
  for attr in ("rhs", "value", "body", "index", "cond", "if_expr", "else_expr"):
    child = getattr(node, attr, None)
    if child is not None and hasattr(child, "copy"):
      _count_sites(rule, child, seen)


def _sites(rule: Any, circuits: list[Any]) -> int:
  seen = [0]
  for circuit in circuits:
    for statement in circuit.statements:
      _count_sites(rule, statement, seen)
  return seen[0]


def run() -> None:
  print("test_rules")

  with contextlib.redirect_stdout(io.StringIO()):
    circuits = [generated(seed) for seed in range(BATCH)]

  for rule in REARRANGEMENTS:
    found = _sites(rule, circuits)
    expect(found > 0, "%s matches generated output (%d sites)" % (rule.name, found))

  violations: list[str] = []
  applied = 0
  for seed, circuit in enumerate(circuits):
    result = rewrite_circuit(circuit, seed=seed, amount=REWRITES_PER_CIRCUIT)
    applied += len(result.rule_names)
    if not _typechecks(result.circuit):
      violations.append("seed %d: %s" % (seed, result.rule_names))
  for bad in violations[:3]:
    print("    " + bad)
  expect(not violations, "%d rewritten circuits typecheck" % BATCH)
  expect(applied > 0, "rules actually fired (%d applications)" % applied)

  mismatched = []
  for seed in REPEAT_SEEDS:
    with contextlib.redirect_stdout(io.StringIO()):
      circuit = generated(seed)
    first = rewrite_circuit(circuit, seed=seed, amount=REWRITES_PER_CIRCUIT)
    second = rewrite_circuit(circuit, seed=seed, amount=REWRITES_PER_CIRCUIT)
    if (first.rule_names != second.rule_names
        or _fingerprint(first.circuit) != _fingerprint(second.circuit)):
      mismatched.append(seed)
  expect(not mismatched, "same seed rewrites identically")
