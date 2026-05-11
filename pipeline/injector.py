"""Stub: Fault Injector (gadget insertion between sync points).

Real impl: walk every tape, identify sync-point PCs, pick a (lo, hi)
gap on a chosen tape, generate a local-only gadget over live
registers, splice it into a deep-copy of the IR. Whitelist of gadget
opcodes enforces the synchronization invariant.

For now: pretend to splice a drift-and-restore gadget on tape 0.
"""
from __future__ import annotations

from pipeline.config import NeedsInjector
from pipeline.types import InjectionRecord, MpspdzProgram, MutatedProgram


def inject_fault(
  program: MpspdzProgram, config: NeedsInjector,
) -> MutatedProgram:
  record = InjectionRecord(
    gadget_kind="drift_and_restore",
    tape_index=0,
    sync_lo_pc=0,
    sync_hi_pc=0,
    party_id=config.malicious_party,
    details=f"STUB: would generate gadget from seed={config.seed.value}",
  )
  print(
    f"[injector] STUB: would splice {record.gadget_kind} "
    f"on tape {record.tape_index} (party {record.party_id})"
  )
  return MutatedProgram(original=program, mutated=program, record=record)
