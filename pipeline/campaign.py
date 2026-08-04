"""Campaign planning: grid expansion and seed allocation.

Deliberately not in `Store`. The store owns rows, leases and results; this owns
which rows exist. It expands protocols x party counts into `ExperimentConfig`
grid points, samples a corrupt set per point (non-empty S subset {0..n-1},
|S| <= t) from one explicit RNG so a campaign replays exactly, and hands each
config a disjoint seed range. Seeds are globally unique across configs because
a seed IS the generated program.

Populating is idempotent (`insert_*` are INSERT OR IGNORE), so a dispatcher
restart reattaches to a live campaign instead of duplicating it.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Iterator, Protocol as View, cast

from pipeline.protocols import PROTOCOL_SPECS
from pipeline.store import ExperimentConfig
from pipeline.types import Protocol

MAX_DEPTH = 40


@dataclass(frozen=True)
class CampaignPlan:
  """The whole campaign in one value: what to cross, how deep, how many."""
  protocols: tuple[Protocol, ...]
  party_counts: tuple[int, ...]
  runs_per_config: int
  start_seed: int = 0
  timeout_s: float = 120.0
  rng_seed: int = 0
  max_depth: int = MAX_DEPTH
  combo: str = "baseline"

  @property
  def grid_points(self) -> list[tuple[Protocol, int]]:
    return [(p, n) for p in self.protocols for n in self.party_counts]

  @property
  def total_runs(self) -> int:
    return len(self.grid_points) * self.runs_per_config


class NeedsCampaign(View):
  """The slice of `Store` the campaign layer writes through."""
  def insert_config(self, config: ExperimentConfig) -> int: ...
  def insert_experiments(self, config_id: int, seeds: Iterable[int]) -> int: ...


def parse_protocols(names: Iterable[str]) -> tuple[Protocol, ...]:
  """Validate CLI protocol names against the spec table; the only cast site."""
  chosen = [n.strip() for n in names if n.strip()]
  unknown = [n for n in chosen if n not in PROTOCOL_SPECS]
  if unknown:
    raise ValueError(f"unknown protocol(s): {unknown}")
  return tuple(cast(Protocol, n) for n in chosen)


def sample_corrupt_set(
  rng: random.Random, protocol: Protocol, n_parties: int,
) -> frozenset[int]:
  """Non-empty S subset {0..n-1} with |S| <= t, sampled, not pinned.

  The round launcher used S = {0..t-1}: always the first t parties, always
  exactly t of them. That is one corner of the threat model, not the model.
  """
  max_corrupt = PROTOCOL_SPECS[protocol].max_corrupt(n_parties)
  if max_corrupt < 1:
    raise ValueError(f"{protocol} at n={n_parties} tolerates no corrupt party")
  size = rng.randint(1, max_corrupt)
  return frozenset(rng.sample(range(n_parties), size))


def expand(plan: CampaignPlan) -> Iterator[tuple[ExperimentConfig, range]]:
  """Grid point -> (config, its disjoint seed range), in a fixed order.

  Order is fixed so the single RNG replays: same `rng_seed`, same corrupt sets
  and same depths.
  """
  rng = random.Random(plan.rng_seed)
  lo = plan.start_seed
  for protocol, n_parties in plan.grid_points:
    config = ExperimentConfig(
      protocol=protocol,
      n_parties=n_parties,
      corrupt_set=sample_corrupt_set(rng, protocol, n_parties),
      expression_depth=rng.randint(1, plan.max_depth),
      combo=plan.combo,
      timeout_s=plan.timeout_s,
    )
    yield config, range(lo, lo + plan.runs_per_config)
    lo += plan.runs_per_config


def populate(store: NeedsCampaign, plan: CampaignPlan) -> int:
  """Write the campaign into the store; returns experiments newly inserted."""
  inserted = 0
  for config, seeds in expand(plan):
    config_id = store.insert_config(config)
    inserted += store.insert_experiments(config_id, seeds)
  return inserted
