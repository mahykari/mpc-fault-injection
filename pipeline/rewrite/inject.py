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

# Field-level sign flip, the port of the `mulsi r, r, -1` gadget. The -1 is
# the operator, not an injected operand, so it stays a literal.
SIGN_FLIP = -1


@dataclass(frozen=True)
class Site:
  node: Any
  stmt_index: int


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
  found = [node]
  for index in range(len(node)):
    found.extend(_walk(node[index]))
  return found


def _sites(circuit: Any, rule: InjectionRule) -> list[Site]:
  found = []
  for index, statement in enumerate(circuit.statements):
    for node in _walk(statement):
      if node is not statement and rule.matches(node):
        found.append(Site(node=node, stmt_index=index))
  return found


@dataclass(frozen=True)
class InjectionResult:
  circuit: Any
  rule_names: tuple[str, ...]


def inject_circuit(circuit: Any, seed: int, amount: int = 1) -> InjectionResult:
  """Apply up to `amount` injections. Fewer when no rule can fire."""
  rng = Random(seed)
  root = circuit.copy()
  applied: list[str] = []
  replacer = NodeReplacer()

  for _ in range(amount):
    options = [(rule, site) for rule in INJECTIONS for site in _sites(root, rule)]
    if not options:
      break
    rule, site = options[rng.randrange(len(options))]
    replacement = rule.build(site, root, rng)
    if replacement is None:
      continue
    if not replacer.replace(root, site.node, replacement):
      continue
    applied.append(rule.name)

  return InjectionResult(circuit=root, rule_names=tuple(applied))
