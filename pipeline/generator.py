"""Stub: Program Generator + CircIL → MP-SPDZ translator.

Real impl will call into python-circil to generate programs and
translate them to MP-SPDZ source. For now: hardcoded tutorial program.
"""
from __future__ import annotations

from pipeline.types import CircilProgram, MpspdzSource, Seed


def generate_program(seed: Seed) -> CircilProgram:
  print(f"[generator] STUB: would generate CircIL program from seed={seed.value}")
  return CircilProgram(
    program_id=f"stub-{seed.value:04d}",
    source="# placeholder CircIL program",
  )


def translate_to_mpspdz(program: CircilProgram) -> MpspdzSource:
  print(f"[translator] STUB: would lower {program.program_id} to MP-SPDZ source")
  # Hardcoded tutorial-shaped program so downstream stubs see something plausible.
  src = (
    "a = sint(1)\n"
    "b = sint(2)\n"
    "c = (a + b).reveal()\n"
    "print_ln('result: %s', c)\n"
  )
  return MpspdzSource(program_id=program.program_id, source=src)
