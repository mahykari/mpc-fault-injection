"""Gadget framework + concrete templates."""
from __future__ import annotations

from pipeline.gadgets.immediate_swap import ImmediateSwapGadget, ImmediateSwapTemplate
from pipeline.gadgets.types import Gadget, GadgetTemplate, SyncGap

__all__ = [
  "Gadget",
  "GadgetTemplate",
  "ImmediateSwapGadget",
  "ImmediateSwapTemplate",
  "SyncGap",
]
