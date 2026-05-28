"""Gadget framework.

A `GadgetTemplate` is a factory keyed to a chosen anchor instruction.
A `Gadget` is a fully-sampled instance ready to mutate the program.
The Injector picks anchors centrally and dispatches to templates.
"""
from __future__ import annotations

from random import Random
from typing import Any, Protocol as View


class Gadget(View):
  @property
  def kind(self) -> str: ...

  @property
  def tape_index(self) -> int: ...

  @property
  def details(self) -> str: ...

  def apply(self, program: Any) -> None: ...


class GadgetTemplate(View):
  @property
  def kind(self) -> str: ...

  def make(self, tape_index: int, anchor: Any, rng: Random) -> Gadget: ...
