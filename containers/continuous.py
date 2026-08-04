"""Continuous fuzzing: one dispatcher, N workers, no rounds.

The dispatcher owns the campaign: it holds the (protocol, party-count, ...)
grid and the seed space in sqlite, hands out one experiment per request, and
records the report that comes back. Workers are long-lived and never idle at a
barrier; each pulls its next experiment the moment the last one finishes, so a
grid point that runs an order of magnitude slower than its neighbours costs
only its own slot, not the whole round.

This script is the campaign launcher: create the shared podman network, start
the dispatcher on it, start the workers on it, wait. Workers back off and retry
while the dispatcher boots, so no ordering sleep is needed. When the campaign
drains, the dispatcher answers 204, every worker exits, and we stop the
dispatcher.

Results live in the dispatcher's sqlite file under runs/, not in per-run
report.json rollups, so there is no per-round aggregate step any more.

Build the images, then fire and walk away:
  ./containers/build.sh pipeline
  ./containers/build.sh dispatch
  uv run python containers/continuous.py --memory 4g --runs 5000
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from launch import (  # noqa: E402  (needs SCRIPT_DIR on path)
  DEFAULT_NETWORK,
  RUNS_DIR,
  ensure_network,
  spawn_worker,
)

DISPATCH_IMAGE = "mpspdz-dispatch:v0.4.2"
DISPATCH_NAME = "dispatcher"
DISPATCH_PORT = 8080
DISPATCH_DB = "/app/runs/campaign.db"
WORKER_IMAGE = "mpspdz-pipeline:v0.4.2"


def parse_args() -> argparse.Namespace:
  p = argparse.ArgumentParser(description=__doc__)
  p.add_argument("--workers", type=int, default=16)
  # Campaign shape belongs to the dispatcher; these are relayed, not interpreted.
  p.add_argument("--runs", type=int, default=5000, help="experiments per grid point")
  p.add_argument("--protocols", default="mascot,spdz2k,malicious-shamir",
                 help="comma-separated; crossed with --party-counts")
  p.add_argument("--party-counts", default="3,5,7,9", help="comma-separated")
  p.add_argument("--start-seed", type=int, default=0)
  p.add_argument("--image", default=WORKER_IMAGE, help="worker image")
  p.add_argument("--dispatch-image", default=DISPATCH_IMAGE)
  p.add_argument("--network", default=DEFAULT_NETWORK)
  # Workers reach the dispatcher over the podman network; this publish is only
  # so `curl localhost:<port>/status` works from the host shell.
  p.add_argument("--status-port", type=int, default=DISPATCH_PORT,
                 help="host port to publish /status on")
  p.add_argument("--memory", default="4g", help="podman --memory per worker")
  p.add_argument("--cpus", help="podman --cpus per worker")
  return p.parse_args()


def dispatcher_url() -> str:
  # Resolved by podman's DNS on the shared network, not by the host.
  return f"http://{DISPATCH_NAME}:{DISPATCH_PORT}"


def campaign_flags(args: argparse.Namespace) -> list[str]:
  """Forwarded verbatim to dispatch.py, which owns the grid and the seed space."""
  return [
    "--runs", str(args.runs),
    "--protocols", args.protocols,
    "--party-counts", args.party_counts,
    "--start-seed", str(args.start_seed),
  ]


def spawn_dispatcher(
  image: str,
  network: str,
  campaign: list[str],
  status_port: int,
) -> "subprocess.Popen[bytes]":
  # Not detached: its stdout joins the campaign log. The DB sits on the mounted
  # runs/ volume, so a restarted dispatcher reattaches to the live campaign.
  # Everything after `image` lands as ENTRYPOINT arguments; dispatch.py reads no
  # environment, so config has to travel as flags.
  return subprocess.Popen([
    "podman", "run", "--rm",
    "--name", DISPATCH_NAME,
    "--network", network,
    "-p", f"{status_port}:{DISPATCH_PORT}",
    "-v", f"{RUNS_DIR}:/app/runs",
    image,
    "--db", DISPATCH_DB,
    "--port", str(DISPATCH_PORT),
    *campaign,
  ])


def main() -> None:
  args = parse_args()
  RUNS_DIR.mkdir(exist_ok=True)
  ensure_network(args.network)

  print(f"=== dispatcher {args.dispatch_image} on {args.network} ===", flush=True)
  dispatcher = spawn_dispatcher(
    args.dispatch_image, args.network, campaign_flags(args), args.status_port)

  print(f"=== {args.workers} workers pulling from {dispatcher_url()} ===", flush=True)
  workers = [
    spawn_worker(
      worker_id, dispatcher_url(), args.network, args.image, args.cpus, args.memory)
    for worker_id in range(args.workers)
  ]

  codes = [(worker_id, p.wait()) for worker_id, p in enumerate(workers)]
  print()
  print("=== campaign drained ===")
  for worker_id, code in codes:
    print(f"  worker {worker_id:02d}: exit {code}")

  subprocess.run(["podman", "stop", DISPATCH_NAME])
  dispatcher.wait()


if __name__ == "__main__":
  main()
