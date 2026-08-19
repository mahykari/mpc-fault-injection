"""Driver over CircIL's `RuleBasedRewriter`.

The library owns the walk, the candidate collection and the splice; this
only fixes the seeding so a run is reproducible, and reports which rules
fired.
"""
from __future__ import annotations

import pipeline.circil as _circil_path_setup  # noqa: F401
from dataclasses import dataclass
from random import Random
from typing import Any

from circil.rewrite.rewriter import RuleBasedRewriter  # type: ignore[import-not-found]
from circil.rewrite.utils import SimpleRNGUtil  # type: ignore[import-not-found]

from pipeline.rewrite.rules import REARRANGEMENTS

# Bound for the literal values SimpleRNGUtil hands to a `$r` in a pattern.
# No rearrangement rule uses one; it is required by the constructor.
_RNG_UTIL_BOUND = 2**31 - 1


@dataclass(frozen=True)
class RewriteResult:
  circuit: Any
  rule_names: tuple[str, ...]


def rewrite_circuit(circuit: Any, seed: int, amount: int = 1) -> RewriteResult:
  rng = Random(seed)
  rewriter = RuleBasedRewriter(
    list(REARRANGEMENTS), SimpleRNGUtil(0, _RNG_UTIL_BOUND, rng), rng
  )
  rewritten, applied = rewriter.run(circuit, amount)
  return RewriteResult(circuit=rewritten, rule_names=tuple(r.name for r in applied))
