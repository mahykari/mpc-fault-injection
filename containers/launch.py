"""Launch N long-lived fuzz workers against an HTTP dispatcher.

Build the image first:  ./containers/build.sh pipeline

A worker pulls one experiment at a time from the dispatcher and exits only
once the campaign drains, so there are no seed slices and no rounds here: we
start the workers and wait once, at the end of the campaign, instead of once
per round at its slowest instance.

Every worker joins one podman network so `http://dispatcher:PORT` resolves via
podman's built-in DNS. Each container still gets its own network namespace, so
the party port probe can't collide across workers; runs/ stays shared.

The dispatcher itself is started by continuous.py, not here.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "runs"
DEFAULT_IMAGE = "mpspdz-pipeline:v0.4.2"
DEFAULT_NETWORK = "fuzz-net"
DEFAULT_DISPATCHER = "http://dispatcher:8080"


def parse_args() -> argparse.Namespace:
  p = argparse.ArgumentParser(description=__doc__)
  p.add_argument("--workers", type=int, required=True, help="worker containers to start")
  p.add_argument("--dispatcher", default=DEFAULT_DISPATCHER, help="base URL workers pull from")
  p.add_argument("--network", default=DEFAULT_NETWORK, help="podman network the dispatcher is on")
  p.add_argument("--image", default=DEFAULT_IMAGE)
  p.add_argument("--cpus", help="podman --cpus per worker, e.g. 2")
  p.add_argument("--memory", help="podman --memory per worker, e.g. 4g")
  return p.parse_args()


def ensure_network(name: str) -> None:
  """Idempotent: a re-launch reattaches to the network the dispatcher is on."""
  if subprocess.run(["podman", "network", "exists", name]).returncode == 0:
    return
  subprocess.run(["podman", "network", "create", name], check=True)


def resource_opts(cpus: str | None, memory: str | None) -> list[str]:
  opts = []
  if cpus is not None:
    opts += ["--cpus", cpus]
  if memory is not None:
    opts += ["--memory", memory]
  return opts


def spawn_worker(
  worker_id: int,
  dispatcher: str,
  network: str,
  image: str,
  cpus: str | None = None,
  memory: str | None = None,
) -> "subprocess.Popen[bytes]":
  # INSTANCE_ID namespaces this worker's run dirs; DISPATCHER is its only input.
  return subprocess.Popen([
    "podman", "run", "--rm",
    "--name", f"fuzz-w{worker_id:02d}",
    "--network", network,
    *resource_opts(cpus, memory),
    "-e", f"INSTANCE_ID={worker_id}",
    "-e", f"DISPATCHER={dispatcher}",
    "-v", f"{RUNS_DIR}:/app/runs",
    image,
  ])


def main() -> None:
  args = parse_args()
  RUNS_DIR.mkdir(exist_ok=True)
  ensure_network(args.network)

  procs = [
    spawn_worker(
      worker_id, args.dispatcher, args.network, args.image, args.cpus, args.memory)
    for worker_id in range(args.workers)
  ]
  # One wait for the whole campaign, not one per round.
  codes = [(worker_id, p.wait()) for worker_id, p in enumerate(procs)]

  print()
  print("=== launch summary ===")
  for worker_id, code in codes:
    print(f"  worker {worker_id:02d}: exit {code}")
  if any(code != 0 for _, code in codes):
    raise SystemExit(1)


if __name__ == "__main__":
  main()
