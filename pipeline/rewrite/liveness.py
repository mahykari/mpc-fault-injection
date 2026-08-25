"""Which statements actually reach an output.

An injection spliced into a value nothing downstream reads cannot change
the revealed result, so the run comes back inert no matter how sound or
unsound the protocol is. Those cases cost a full twin execution and tell
us nothing, and they are the bulk of the historical inert verdicts.

Statement granularity, computed by one backward pass. Coarse on purpose:
inside a live statement every node feeds that statement's value, apart
from dead `let` bindings, and chasing those is not worth the machinery.
"""
from __future__ import annotations

import pipeline.circil as _circil_path_setup  # noqa: F401
from typing import Any

from circil.ir.node import Assignment, Identifier  # type: ignore[import-not-found]

from pipeline.rewrite.donors import free_names


def live_statements(circuit: Any) -> set[int]:
  """Indices of statements whose value reaches a circuit output."""
  needed = {signal.name for signal in circuit.outputs}
  live: set[int] = set()

  for index in reversed(range(len(circuit.statements))):
    statement = circuit.statements[index]
    if not isinstance(statement, Assignment) or not isinstance(statement.lhs, Identifier):
      # Anything we cannot reason about stays live rather than silently
      # dropping a real injection site.
      live.add(index)
      continue
    if statement.lhs.name not in needed:
      continue
    live.add(index)
    # The assignment kills earlier definitions of the same name, so drop
    # it before adding what this right-hand side reads.
    needed.discard(statement.lhs.name)
    needed |= free_names(statement.rhs)

  return live
