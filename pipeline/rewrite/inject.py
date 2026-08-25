"""Injection rules: introduce a term the match did not bind.

Deliberately semantics-breaking. These are the source-level equivalent
of the bytecode bump and sign-flip gadgets, and the thing the harness
actually fuzzes; the rearrangements next door are the control arm.

Matching and construction both live here rather than in a CircIL
pattern. A pattern can only build a term out of what the match bound or
what `$r` synthesises, and a synthesised literal is exactly what an
injected operand must not be: the operand is *selected* from the
circuit by `donors`, so it typechecks by construction and is a real
subexpression. A rule with no admissible donor does not fire, which is
a no-op and not an error.
"""
from __future__ import annotations

import pipeline.circil as _circil_path_setup  # noqa: F401
from dataclasses import dataclass
from random import Random
from typing import Any, Callable

import circil.ir.types as IRType  # type: ignore[import-not-found]
from circil.ir.node import Assignment, IRNode  # type: ignore[import-not-found]
from circil.ir.visitor import NodeReplacer  # type: ignore[import-not-found]

from pipeline.circil_ir import call, integer, is_call, is_field, type_of
from pipeline.matrix import ADD, MATMUL
from pipeline.rewrite.donors import pick_donor
from pipeline.evaluate import diverges
from pipeline.rewrite.liveness import live_statements

# Field-level sign flip, the port of the `mulsi r, r, -1` gadget. The -1 is
# the operator, not an injected operand, so it stays a literal.
SIGN_FLIP = -1


@dataclass(frozen=True)
class Site:
  """Where a rule matched, addressed by position rather than identity.

  `IRNode.copy()` hands out a fresh `node_id`, so a node reference does
  not survive into a copied circuit. A path of child indices does.
  """
  node: Any
  stmt_index: int
  path: tuple[int, ...]


def _matmul_sites(node: Any) -> bool:
  return is_call(node, MATMUL) and len(node.arguments) == 2


def _field_sites(node: Any) -> bool:
  return is_field(node) and not isinstance(node, Assignment)


def _build_matmul_add(site: Site, circuit: Any, rng: Random) -> Any | None:
  """(matmul ?a ?b) -> (matmul (add ?a ?r) ?b)"""
  left, right = site.node.arguments
  wanted = type_of(left)
  if wanted is None:
    return None
  donor = pick_donor(circuit, site.stmt_index, wanted, rng)
  if donor is None:
    return None
  perturbed = call(ADD, [left.copy(), donor], wanted)
  return call(MATMUL, [perturbed, right.copy()], type_of(site.node))


def _build_field_bump(site: Site, circuit: Any, rng: Random) -> Any | None:
  """a -> (a + r), the source-level port of the bump gadget."""
  wanted = IRType.Field()
  donor = pick_donor(circuit, site.stmt_index, wanted, rng)
  if donor is None:
    return None
  return call("+", [site.node.copy(), donor], wanted)


def _build_field_signflip(site: Site, circuit: Any, rng: Random) -> Any | None:
  """a -> (a * -1), the source-level port of the sign-flip gadget."""
  return call("*", [site.node.copy(), integer(SIGN_FLIP)], IRType.Field())


@dataclass(frozen=True)
class InjectionRule:
  name: str
  matches: Callable[[Any], bool]
  build: Callable[[Site, Any, Random], Any | None]


INJECTIONS: tuple[InjectionRule, ...] = (
  InjectionRule("matmul-add-donor", _matmul_sites, _build_matmul_add),
  InjectionRule("field-bump-donor", _field_sites, _build_field_bump),
  InjectionRule("field-signflip", _field_sites, _build_field_signflip),
)


def _walk(node: Any) -> list[Any]:
  return [found for found, _ in _walk_paths(node, ())]


def _walk_paths(node: Any, prefix: tuple[int, ...]) -> list[tuple[Any, tuple[int, ...]]]:
  found = [(node, prefix)]
  for index in range(len(node)):
    found.extend(_walk_paths(node[index], prefix + (index,)))
  return found


def node_at(root: Any, path: tuple[int, ...]) -> Any:
  current = root
  for index in path:
    current = current[index]
  return current


def _sites(circuit: Any, rule: InjectionRule) -> list[Site]:
  """Match sites, restricted to statements that reach an output.

  Splicing into a dead statement produces a mutation that cannot change
  the result, which burns a twin run to learn nothing.
  """
  live = live_statements(circuit)
  found = []
  for index, statement in enumerate(circuit.statements):
    if index not in live:
      continue
    for node, path in _walk_paths(statement, ()):
      if path and rule.matches(node):
        found.append(Site(node=node, stmt_index=index, path=path))
  return found


@dataclass(frozen=True)
class InjectionResult:
  circuit: Any
  rule_names: tuple[str, ...]


def _candidates(circuit: Any, rng: Random) -> list[tuple[InjectionRule, Site]]:
  """Every (rule, site) pair, shuffled so the search order is seeded."""
  options = [(rule, site) for rule in INJECTIONS for site in _sites(circuit, rule)]
  rng.shuffle(options)
  return options


def _apply_one(origin: Any, circuit: Any, rng: Random) -> tuple[Any, str] | None:
  """One output-changing injection applied to a copy of `circuit`.

  Candidates are tried in seeded order, each on its own copy so a
  rejected attempt leaves nothing behind. Divergence is measured against
  `origin`, the unmutated circuit, so a second injection cannot quietly
  cancel the first.
  """
  for rule, site in _candidates(circuit, rng):
    attempt = circuit.copy()
    target = node_at(attempt.statements[site.stmt_index], site.path)
    located = Site(node=target, stmt_index=site.stmt_index, path=site.path)
    replacement = rule.build(located, attempt, rng)
    if replacement is None:
      continue
    if not NodeReplacer().replace(attempt, target, replacement):
      continue
    if diverges(origin, attempt):
      return attempt, rule.name
  return None


def inject_circuit(circuit: Any, seed: int, amount: int = 1) -> InjectionResult:
  """Apply up to `amount` injections, each one output-changing."""
  rng = Random(seed)
  root = circuit.copy()
  applied: list[str] = []

  for _ in range(amount):
    outcome = _apply_one(circuit, root, rng)
    if outcome is None:
      break
    root, name = outcome
    applied.append(name)

  return InjectionResult(circuit=root, rule_names=tuple(applied))
