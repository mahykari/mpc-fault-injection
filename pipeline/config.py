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
from random import Random
from typing import Protocol as View

from pipeline.protocols import PROTOCOL_SPECS, ProtocolSpec
from pipeline.types import Protocol, Seed


@dataclass(frozen=True)
class Config:
  mpspdz_root: Path
  runs_root: Path
  seed: Seed
  protocol: Protocol
  n_parties: int
  malicious_parties: list[int]
  timeout_s: float
  use_patched_binary: bool = False
  seeded_bug_binary: bool = False
  expression_depth: int = 20
  let_probability: float = 0.6
  instance_id: int = 0
  combo: str = "baseline"

  def __post_init__(self) -> None:
    spec = self.spec
    max_corrupt = spec.max_corrupt(self.n_parties)
    if not 1 <= len(self.malicious_parties) <= max_corrupt:
      raise ValueError(
        f"{self.protocol}: corrupt set size {len(self.malicious_parties)} "
        f"outside [1, {max_corrupt}] for n={self.n_parties}")
    if any(p not in range(self.n_parties) for p in self.malicious_parties):
      raise ValueError(
        f"corrupt party ids {self.malicious_parties} outside range(0, {self.n_parties})")

  @property
  def spec(self) -> ProtocolSpec:
    return PROTOCOL_SPECS[self.protocol]

  @property
  def program_rng(self) -> Random:
    return self._stream("program")

  @property
  def gadget_rng(self) -> Random:
    return self._stream("gadgets")

  def _stream(self, purpose: str) -> Random:
    return Random(f"{self.seed.value}:{purpose}")

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


class NeedsGenerator(View):
  @property
  def seed(self) -> Seed: ...
  @property
  def program_rng(self) -> Random: ...
  @property
  def expression_depth(self) -> int: ...
  @property
  def let_probability(self) -> float: ...


class NeedsInjector(View):
  @property
  def program_id(self) -> str: ...
  @property
  def malicious_parties(self) -> list[int]: ...
  @property
  def gadget_rng(self) -> Random: ...


class NeedsCompilerToolkit(View):
  @property
  def mpspdz_root(self) -> Path: ...
  @property
  def spec(self) -> ProtocolSpec: ...


class NeedsPartyBinary(View):
  @property
  def party_binary_path(self) -> Path: ...
  @property
  def program_id(self) -> str: ...
  @property
  def spec(self) -> ProtocolSpec: ...
  @property
  def timeout_s(self) -> float: ...


class NeedsOracle(View):
  @property
  def spec(self) -> ProtocolSpec: ...


class NeedsCompiler(View):
  @property
  def program_id(self) -> str: ...


class NeedsSslProvisioner(View):
  @property
  def mpspdz_root(self) -> Path: ...
  @property
  def n_parties(self) -> int: ...


class NeedsExecutor(View):
  @property
  def program_id(self) -> str: ...
  @property
  def timeout_s(self) -> float: ...
  @property
  def spec(self) -> ProtocolSpec: ...
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
  @property
  def combo(self) -> str: ...
  @property
  def protocol(self) -> Protocol: ...
  @property
  def n_parties(self) -> int: ...
