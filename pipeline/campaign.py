"""Campaign planning: which experiments exist.

Deliberately not in `Store`. The store owns rows, leases and results; this owns
which rows exist. It crosses protocols with party counts into grid points,
draws each point's corrupt set (non-empty S subset {0..n-1}, |S| <= t) and
depth from one RNG so a campaign replays exactly, and hands each point a
disjoint seed range. Seeds are globally unique across points because a seed IS
the generated program.

Populating is idempotent (`insert_*` are INSERT OR IGNORE), so a dispatcher
restart reattaches to a live campaign instead of duplicating it.
"""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Iterable, cast

from pipeline.protocols import PROTOCOL_SPECS
from pipeline.store import ExperimentConfig, Store
from pipeline.types import Protocol

MAX_DEPTH = 40


@dataclass(frozen=True)
class CampaignPlan:
  """The whole campaign in one value: what to cross, how deep, how many."""
  protocols: tuple[Protocol, ...]
  party_counts: tuple[int, ...]
  runs_per_point: int
  start_seed: int = 0
  timeout_s: float = 120.0
  rng_seed: int = 0
  max_depth: int = MAX_DEPTH
  combo: str = "baseline"

  def __post_init__(self) -> None:
    for protocol, n_parties in self.grid_points:
      if PROTOCOL_SPECS[protocol].max_corrupt(n_parties) < 1:
        raise ValueError(f"{protocol} at n={n_parties} tolerates no corrupt party")

  @property
  def grid_points(self) -> list[tuple[Protocol, int]]:
    return [(p, n) for p in self.protocols for n in self.party_counts]

  @property
  def total_runs(self) -> int:
    return len(self.grid_points) * self.runs_per_point


def parse_protocols(names: Iterable[str]) -> tuple[Protocol, ...]:
  """Validate CLI protocol names against the spec table; the only cast site."""
  chosen = [n.strip() for n in names if n.strip()]
  unknown = [n for n in chosen if n not in PROTOCOL_SPECS]
  if unknown:
    raise ValueError(f"unknown protocol(s): {unknown}")
  return tuple(cast(Protocol, n) for n in chosen)


def sample_corrupt_set(rng: Random, protocol: Protocol, n_parties: int) -> frozenset[int]:
  """Non-empty S subset {0..n-1} with |S| <= t."""
  size = rng.randint(1, PROTOCOL_SPECS[protocol].max_corrupt(n_parties))
  return frozenset(rng.sample(range(n_parties), size))


def populate(store: Store, plan: CampaignPlan) -> int:
  """Write the campaign into the store; returns experiments newly inserted.

  Grid points go in a fixed order so one RNG replays: same `rng_seed`, same
  corrupt sets and depths.
  """
  rng = Random(plan.rng_seed)
  inserted = 0
  seed = plan.start_seed
  for protocol, n_parties in plan.grid_points:
    point = ExperimentConfig(
      protocol=protocol,
      n_parties=n_parties,
      corrupt_set=sample_corrupt_set(rng, protocol, n_parties),
      expression_depth=rng.randint(1, plan.max_depth),
      combo=plan.combo,
      timeout_s=plan.timeout_s,
    )
    config_id = store.insert_config(point)
    inserted += store.insert_experiments(
      config_id, range(seed, seed + plan.runs_per_point))
    seed += plan.runs_per_point
  return inserted
