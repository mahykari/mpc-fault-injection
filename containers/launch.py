"""Launch N fuzz-pipeline containers concurrently against a shared runs/.

Build the image first:  ./containers/build.sh pipeline

Each instance gets a disjoint, reproducible slice of seeds (sampled under
--seed). We write one JSON run spec per instance — its seeds, its instance_id,
plus any tunables from --config — and mount it as the container's only input;
the container reads it via CONFIG. Containers keep their own network namespace
(default bridge), so the party port probe can't collide; only runs/ is shared.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "runs"
DEFAULT_IMAGE = "mpspdz-pipeline:v0.4.2"
CONFIG_MOUNT = "/app/config.json"
MAX_DEPTH = 40


def parse_args() -> argparse.Namespace:
  p = argparse.ArgumentParser(description=__doc__)
  p.add_argument("--instances", type=int, required=True)
  p.add_argument("--runs", type=int, default=50, help="seeds per instance")
  p.add_argument("--seed", type=int, default=0, help="seeds the seed sampling")
  p.add_argument("--pool", type=int, default=100_000, help="seed space to sample from")
  p.add_argument("--image", default=DEFAULT_IMAGE)
  p.add_argument("--cpus", help="podman --cpus per instance, e.g. 2")
  p.add_argument("--memory", help="podman --memory per instance, e.g. 4g")
  p.add_argument("--config", help="JSON of tunables, merged into every instance's spec")
  p.add_argument("--disabled-sites", help="comma-separated site IDs to disable MAC staging")
  return p.parse_args()


def seed_slices(instances: int, runs: int, pool: int, seed: int) -> list[list[int]]:
  total = instances * runs
  if total > pool:
    raise SystemExit(f"need {total} distinct seeds but pool is {pool}; raise --pool")
  chosen = random.Random(seed).sample(range(pool), total)
  return [chosen[i * runs:(i + 1) * runs] for i in range(instances)]


def instance_depths(instances: int, seed: int) -> list[int]:
  rng = random.Random(seed)
  return [rng.randint(1, MAX_DEPTH) for _ in range(instances)]


def spawn(
  instance_id: int,
  config: Path,
  image: str,
  cpus: str | None = None,
  memory: str | None = None,
  disabled_sites: str | None = None,
) -> "subprocess.Popen[bytes]":
  opts = []
  if cpus is not None:
    opts += ["--cpus", cpus]
  if memory is not None:
    opts += ["--memory", memory]
  env_opts = ["-e", f"CONFIG={CONFIG_MOUNT}"]
  if disabled_sites:
    env_opts += ["-e", f"MPSPDZ_DISABLED_SITES={disabled_sites}"]
  return subprocess.Popen([
    "podman", "run", "--rm",
    "--name", f"fuzz-i{instance_id:02d}",
    *opts,
    "-v", f"{config}:{CONFIG_MOUNT}:ro",
    *env_opts,
    "-v", f"{RUNS_DIR}:/app/runs",
    image,
  ])


def main() -> None:
  args = parse_args()
  RUNS_DIR.mkdir(exist_ok=True)
  tunables: dict[str, Any] = json.loads(Path(args.config).read_text()) if args.config else {}
  slices = seed_slices(args.instances, args.runs, args.pool, args.seed)
  depths = instance_depths(args.instances, args.seed)

  specs_dir = Path(tempfile.mkdtemp(prefix="fuzz-specs-"))
  procs = []
  for i, seeds in enumerate(slices):
    spec = {**tunables, "seeds": seeds, "instance_id": i, "expression_depth": depths[i]}
    spec_path = specs_dir / f"i{i:02d}.json"
    spec_path.write_text(json.dumps(spec))
    procs.append(spawn(i, spec_path, args.image, args.cpus, args.memory, args.disabled_sites))
  codes = [(i, p.wait()) for i, p in enumerate(procs)]

  print()
  print("=== launch summary ===")
  for instance_id, code in codes:
    print(f"  instance {instance_id:02d}: exit {code}")
  if any(code != 0 for _, code in codes):
    raise SystemExit(1)


if __name__ == "__main__":
  main()
