"""Campaign launcher: one dispatcher, N pull workers, no rounds.

Everything runs in podman containers on one named podman network. Each
container has its own network namespace, so `dispatcher` resolves as a
hostname only because both sides sit on that network: creating the network
makes the name resolvable, starting a container "on it" attaches the
container. The same isolation keeps the workers' MP-SPDZ party ports from
colliding. runs/ is mounted into every container, so the dispatcher's sqlite
file and the workers' run dirs land on the host.

Campaign shape (--runs, --protocols, --party-counts, ...) is not parsed here:
every flag this script does not know is forwarded to the dispatcher, which
owns it. Workers back off and retry while the dispatcher boots, so nothing
sleeps. When the campaign drains the dispatcher answers 204, every worker
exits, and the dispatcher is stopped.

  ./containers/build.sh pipeline
  ./containers/build.sh dispatch
  python3 containers/launch.py --memory 4g --runs 5000
"""
from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"
CONTAINER_RUNS_DIR = "/app/runs"
DISPATCH_NAME = "dispatcher"
DISPATCH_PORT = 8080
DISPATCHER_URL = f"http://{DISPATCH_NAME}:{DISPATCH_PORT}"
# A party spawns ~230 threads, so a 9-party run needs ~2050 and podman's 2048
# default denies the last few. MP-SPDZ does not fail on that, it deadlocks:
# peers sit in accept() for a party whose connection thread was never created.
PIDS_UNLIMITED = "0"


@dataclass(frozen=True)
class Launch:
  """Everything the launcher owns: podman knobs plus the forwarded campaign flags."""
  workers: int
  worker_image: str
  dispatch_image: str
  network: str
  status_port: int
  cpus: str | None
  memory: str | None
  campaign: list[str]

  @classmethod
  def from_argv(cls, argv: list[str] | None = None) -> "Launch":
    p = argparse.ArgumentParser(
      description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--workers", type=int, default=16, help="worker containers to start")
    p.add_argument("--worker-image", default="mpspdz-pipeline:v0.4.2")
    p.add_argument("--dispatch-image", default="fuzz-dispatch")
    p.add_argument("--network", default="fuzz-net",
                   help="podman network shared by every container")
    p.add_argument("--status-port", type=int, default=DISPATCH_PORT,
                   help="host port for curl localhost:PORT/status")
    p.add_argument("--cpus", help="podman --cpus per worker, e.g. 2")
    p.add_argument("--memory", help="podman --memory per worker, e.g. 4g")
    known, campaign = p.parse_known_args(argv)
    return cls(
      workers=known.workers,
      worker_image=known.worker_image,
      dispatch_image=known.dispatch_image,
      network=known.network,
      status_port=known.status_port,
      cpus=known.cpus,
      memory=known.memory,
      campaign=campaign,
    )

  @property
  def worker_resources(self) -> list[str]:
    opts = ["--pids-limit", PIDS_UNLIMITED]
    if self.cpus is not None:
      opts += ["--cpus", self.cpus]
    if self.memory is not None:
      opts += ["--memory", self.memory]
    return opts

  @property
  def runs_mount(self) -> str:
    return f"{RUNS_DIR}:{CONTAINER_RUNS_DIR}"


def ensure_network(name: str) -> None:
  if subprocess.run(["podman", "network", "exists", name]).returncode == 0:
    return
  subprocess.run(["podman", "network", "create", name], check=True)


def spawn_dispatcher(launch: Launch) -> "subprocess.Popen[bytes]":
  # Not detached: its stdout joins the campaign log.
  return subprocess.Popen([
    "podman", "run", "--rm",
    "--name", DISPATCH_NAME,
    "--network", launch.network,
    "-p", f"{launch.status_port}:{DISPATCH_PORT}",
    "-v", launch.runs_mount,
    launch.dispatch_image,
    "--db", f"{CONTAINER_RUNS_DIR}/campaign.db",
    "--port", str(DISPATCH_PORT),
    *launch.campaign,
  ])


def spawn_worker(launch: Launch, worker_id: int) -> "subprocess.Popen[bytes]":
  return subprocess.Popen([
    "podman", "run", "--rm",
    "--name", f"fuzz-w{worker_id:02d}",
    "--network", launch.network,
    *launch.worker_resources,
    "-e", f"INSTANCE_ID={worker_id}",
    "-e", f"DISPATCHER={DISPATCHER_URL}",
    "-v", launch.runs_mount,
    launch.worker_image,
  ])


def main(launch: Launch) -> None:
  RUNS_DIR.mkdir(exist_ok=True)
  ensure_network(launch.network)

  print(f"=== dispatcher {launch.dispatch_image} on {launch.network} ===", flush=True)
  dispatcher = spawn_dispatcher(launch)

  print(f"=== {launch.workers} workers pulling from {DISPATCHER_URL} ===", flush=True)
  workers = [spawn_worker(launch, worker_id) for worker_id in range(launch.workers)]

  codes = [(worker_id, p.wait()) for worker_id, p in enumerate(workers)]
  print()
  print("=== campaign drained ===")
  for worker_id, code in codes:
    print(f"  worker {worker_id:02d}: exit {code}")

  subprocess.run(["podman", "stop", DISPATCH_NAME])
  dispatcher.wait()


if __name__ == "__main__":
  main(Launch.from_argv())
