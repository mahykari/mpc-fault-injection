"""Master Config and per-component views.

One frozen `Config` is the pipeline-run's source of truth. Every
derived value (paths, the binary location, the per-twin cwd lists)
is a `@property`, so each relation lives in exactly one place.

Each component declares a `Needs<Component>(View)` — a structural
view stating which Config properties it reads. Pass the full Config
to each component; annotate the parameter with the view. mypy then
documents the per-component slice.
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol as View

from pipeline.types import Protocol, Seed


@dataclass(frozen=True)
class Config:
  mpspdz_root: Path
  runs_root: Path
  seed: Seed
  protocol: Protocol
  n_parties: int
  field_prime: int
  malicious_parties: tuple[int, ...]
  timeout_s: float
  use_patched_binary: bool = False
  seeded_bug_binary: bool = False
  expression_depth: int = 20
  let_probability: float = 0.6
  instance_id: int = 0

  @property
  def program_id(self) -> str:
    return f"i{self.instance_id:02d}-case-{self.seed.value:04d}"

  @property
  def party_binary_path(self) -> Path:
    if self.seeded_bug_binary:
      bin_dir = "Linux-amd64-patched-seeded-bug"
    elif self.use_patched_binary:
      bin_dir = "Linux-amd64-patched"
    else:
      bin_dir = "Linux-amd64"
    return self.mpspdz_root / "bin" / bin_dir / f"{self.protocol}-party.x"

  @property
  def run_dir(self) -> Path:
    return self.runs_root / self.program_id

  @property
  def honest_dir(self) -> Path:
    return self.run_dir / "honest"

  @property
  def mutated_dir(self) -> Path:
    return self.run_dir / "mutated"

  @property
  def honest_party_cwds(self) -> tuple[Path, ...]:
    return tuple(self.honest_dir for _ in range(self.n_parties))

  @property
  def mutated_party_cwds(self) -> tuple[Path, ...]:
    corrupt = frozenset(self.malicious_parties)
    return tuple(
      self.mutated_dir if i in corrupt else self.honest_dir
      for i in range(self.n_parties)
    )

  @property
  def report_path(self) -> Path:
    return self.run_dir / "report.json"


# Program-derived (paths) or per-run (seed/instance); not user-tunable.
_PROTECTED_FIELDS = frozenset({"mpspdz_root", "runs_root", "seed", "instance_id"})


def load_overrides(defaults: Config, path: Path) -> Config:
  """Build a Config by overlaying a partial JSON dict onto `defaults`.

  Keys absent from the file keep their default. Protected and unknown keys
  raise rather than pass silently. `malicious_parties` arrives as a JSON
  array and is coerced to the tuple Config expects.
  """
  with open(path) as f:
    overrides = json.load(f)
  field_names = {f.name for f in dataclasses.fields(Config)}
  for key in overrides:
    if key in _PROTECTED_FIELDS:
      raise ValueError(f"config key {key!r} is program-controlled, not overridable")
    if key not in field_names:
      raise ValueError(f"unknown config key {key!r}")
  if "malicious_parties" in overrides:
    overrides["malicious_parties"] = tuple(overrides["malicious_parties"])
  return dataclasses.replace(defaults, **overrides)


class NeedsGenerator(View):
  @property
  def seed(self) -> Seed: ...
  @property
  def expression_depth(self) -> int: ...
  @property
  def let_probability(self) -> float: ...

class NeedsInjector(View):
  @property
  def program_id(self) -> str: ...
  @property
  def malicious_parties(self) -> tuple[int, ...]: ...
  @property
  def seed(self) -> Seed: ...


class NeedsCompilerToolkit(View):
  @property
  def mpspdz_root(self) -> Path: ...


class NeedsPartyBinary(View):
  @property
  def party_binary_path(self) -> Path: ...
  @property
  def program_id(self) -> str: ...
  @property
  def field_prime(self) -> int: ...
  @property
  def timeout_s(self) -> float: ...


class NeedsCompiler(View):
  @property
  def program_id(self) -> str: ...


class NeedsExecutor(View):
  @property
  def program_id(self) -> str: ...
  @property
  def timeout_s(self) -> float: ...
  @property
  def honest_dir(self) -> Path: ...
  @property
  def mutated_dir(self) -> Path: ...
  @property
  def honest_party_cwds(self) -> tuple[Path, ...]: ...
  @property
  def mutated_party_cwds(self) -> tuple[Path, ...]: ...


class NeedsReporter(View):
  @property
  def report_path(self) -> Path: ...
