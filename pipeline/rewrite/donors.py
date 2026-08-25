"""Finding an existing node to reuse as an injected operand.

An injection rule needs a term the match did not bind. Rather than
synthesise one, take a node already in the circuit: it typechecks by
construction and it produces a real subexpression instead of a literal.

Scope is handled conservatively. A donor is admissible only when every
identifier it mentions is a circuit input or the target of an earlier
assignment, both of which are in scope everywhere downstream. That
rejects anything reaching a `let`-bound name, including donors that
would in fact have been fine. Losing candidates is cheap; splicing an
out-of-scope name is not.
"""
from __future__ import annotations

import pipeline.circil as _circil_path_setup  # noqa: F401
from random import Random
from typing import Any

from circil.ir.node import (  # type: ignore[import-not-found]
  Assignment,
  Identifier,
  IRNode,
  LetExpression,
)

from pipeline.circil_ir import type_of

# Calls whose result costs preprocessed material. Copying one into a
# mutated twin makes that twin need more offline data than the honest
# one, and the two parties then size their offline phase differently.
# `*` is listed because a product of two secrets consumes a triple; a
# product with a constant does not, but telling them apart here is not
# worth the precision.
COSTLY_CALLS = frozenset({"matmul", "*"})


def _walk(node: Any) -> list[Any]:
  found = [node]
  for index in range(len(node)):
    found.extend(_walk(node[index]))
  return found


def free_names(node: Any) -> set[str]:
  """Identifier names the node reads, minus the ones it binds itself."""
  names: set[str] = set()
  bound: set[str] = set()
  for current in _walk(node):
    if isinstance(current, LetExpression):
      bound.add(current.var)
    elif isinstance(current, Identifier):
      names.add(current.name)
  return names - bound


def visible_names(circuit: Any, before: int) -> set[str]:
  """Names in scope for every position at or after statement `before`."""
  names = {signal.name for signal in circuit.inputs}
  for statement in circuit.statements[:before]:
    if isinstance(statement, Assignment) and isinstance(statement.lhs, Identifier):
      names.add(statement.lhs.name)
  return names


def donors_of_type(circuit: Any, before: int, wanted: Any) -> list[Any]:
  """Every in-scope node of `wanted` type, in a stable pre-order."""
  scope = visible_names(circuit, before)
  found = []
  for signal in circuit.inputs:
    if _admissible(signal, wanted, scope):
      found.append(signal)
  for statement in circuit.statements[:before]:
    for node in _walk(statement):
      if _admissible(node, wanted, scope):
        found.append(node)
  return found


def costs_preprocessing(node: Any) -> bool:
  """True when copying this subtree would add offline work."""
  return any(
    getattr(getattr(current, "function", None), "name", None) in COSTLY_CALLS
    for current in _walk(node)
  )


def _admissible(node: Any, wanted: Any, scope: set[str]) -> bool:
  if isinstance(node, (Assignment, LetExpression)):
    return False
  found = type_of(node)
  if found is None or not found.equiv(wanted) or found.is_generic:
    return False
  if costs_preprocessing(node):
    return False
  return free_names(node) <= scope


def pick_donor(circuit: Any, before: int, wanted: Any, rng: Random) -> Any | None:
  """One donor, or None when the rule cannot fire."""
  candidates = donors_of_type(circuit, before, wanted)
  if not candidates:
    return None
  return candidates[rng.randrange(len(candidates))].copy()
