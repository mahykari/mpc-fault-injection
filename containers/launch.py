"""Launch N fuzz-pipeline containers concurrently against a shared runs/.

Build the image first:  ./containers/build.sh pipeline

Each instance gets a disjoint, reproducible slice of seeds (sampled under
--seed) and its own INSTANCE_ID, which namespaces its artifacts as
runs/i<NN>-case-*. Containers keep their own network namespace (default
bridge), so the party port probe can't collide across instances; only runs/
is shared.
"""
from __future__ import annotations

import argparse
import random
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "runs"
DEFAULT_IMAGE = "mpspdz-pipeline:v0.4.2"


def parse_args() -> argparse.Namespace:
  p = argparse.ArgumentParser(description=__doc__)
  p.add_argument("--instances", type=int, required=True)
  p.add_argument("--runs", type=int, default=50, help="seeds per instance")
  p.add_argument("--seed", type=int, default=0, help="seeds the seed sampling")
  p.add_argument("--pool", type=int, default=100_000, help="seed space to sample from")
  p.add_argument("--image", default=DEFAULT_IMAGE)
  p.add_argument("--cpus", help="podman --cpus per instance, e.g. 2")
  p.add_argument("--memory", help="podman --memory per instance, e.g. 4g")
  p.add_argument("--config", help="host path to a JSON config, mounted into every instance")
  return p.parse_args()


def seed_slices(instances: int, runs: int, pool: int, seed: int) -> list[list[int]]:
  total = instances * runs
  if total > pool:
    raise SystemExit(f"need {total} distinct seeds but pool is {pool}; raise --pool")
  chosen = random.Random(seed).sample(range(pool), total)
  return [chosen[i * runs:(i + 1) * runs] for i in range(instances)]


CONFIG_MOUNT = "/app/config.json"


def spawn(
  instance_id: int,
  seeds: list[int],
  image: str,
  cpus: str | None = None,
  memory: str | None = None,
  config: Path | None = None,
) -> "subprocess.Popen[bytes]":
  opts = []
  if cpus is not None:
    opts += ["--cpus", cpus]
  if memory is not None:
    opts += ["--memory", memory]
  if config is not None:
    opts += ["-v", f"{config}:{CONFIG_MOUNT}:ro", "-e", f"CONFIG={CONFIG_MOUNT}"]
  return subprocess.Popen([
    "podman", "run", "--rm",
    "--name", f"fuzz-i{instance_id:02d}",
    *opts,
    "-e", f"INSTANCE_ID={instance_id}",
    "-e", "SEEDS=" + ",".join(map(str, seeds)),
    "-v", f"{RUNS_DIR}:/app/runs",
    image,
  ])


def main() -> None:
  args = parse_args()
  RUNS_DIR.mkdir(exist_ok=True)
  slices = seed_slices(args.instances, args.runs, args.pool, args.seed)
  config = Path(args.config).resolve() if args.config else None
  procs = [
    spawn(i, seeds, args.image, args.cpus, args.memory, config)
    for i, seeds in enumerate(slices)
  ]
  codes = [(i, p.wait()) for i, p in enumerate(procs)]

  print()
  print("=== launch summary ===")
  for instance_id, code in codes:
    print(f"  instance {instance_id:02d}: exit {code}")
  if any(code != 0 for _, code in codes):
    raise SystemExit(1)


if __name__ == "__main__":
  main()
