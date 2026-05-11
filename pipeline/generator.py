"""Stub: Program Generator + CircIL → MP-SPDZ translator.

Real impl will call into python-circil to generate programs and
translate them to MP-SPDZ source. For now: hardcoded tutorial program.
"""
from __future__ import annotations

from pipeline.config import NeedsGenerator
from pipeline.types import CircilProgram, MpspdzSource


def generate_program(config: NeedsGenerator) -> CircilProgram:
  print(f"[generator] STUB: placeholder CircIL (seed={config.seed.value})")
  return CircilProgram(source="# placeholder CircIL program")


def translate_to_mpspdz(program: CircilProgram) -> MpspdzSource:
  print(f"[translator] STUB: ignoring {len(program.source)}-byte CircIL")
  src = (
    "a = sint(1)\n"
    "b = sint(2)\n"
    "c = (a + b).reveal()\n"
    "print_ln('result: %s', c)\n"
  )
  return MpspdzSource(source=src)
