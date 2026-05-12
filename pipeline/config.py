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
  malicious_party: int
  timeout_s: float
  use_patched_binary: bool = False

  @property
  def program_id(self) -> str:
    return f"stub-{self.seed.value:04d}"

  @property
  def party_binary_path(self) -> Path:
    bin_dir = "Linux-amd64-patched" if self.use_patched_binary else "Linux-amd64"
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
    return tuple(
      self.mutated_dir if i == self.malicious_party else self.honest_dir
      for i in range(self.n_parties)
    )

  @property
  def report_path(self) -> Path:
    return self.run_dir / "report.json"


class NeedsGenerator(View):
  @property
  def seed(self) -> Seed: ...


class NeedsInjector(View):
  @property
  def program_id(self) -> str: ...
  @property
  def malicious_party(self) -> int: ...


class NeedsCompilerToolkit(View):
  @property
  def mpspdz_root(self) -> Path: ...


class NeedsPartyBinary(View):
  @property
  def party_binary_path(self) -> Path: ...


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
