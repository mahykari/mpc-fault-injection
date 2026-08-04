"""Campaign dispatcher: hands experiments to workers over HTTP, records results.

Replaces the round barrier (launch.py + continuous.py): no fixed seed slices,
no waiting on the slowest instance. A worker pulls one experiment at a time and
only stops when `GET /next` answers 204, which means the campaign is drained.

  GET  /next    200 + claimed payload | 204 (drained)
  POST /result  {"experiment_id", "report"} -> 204
  GET  /status  200 + verdict counts

Stdlib only, so the image is python:3.12-slim and rebuilds in seconds.

  python containers/dispatch.py --db runs/campaign.db --runs 5000
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.campaign import CampaignPlan, parse_protocols, populate  # noqa: E402
from pipeline.store import Store  # noqa: E402
from pipeline.wire import claimed_to_payload, report_from_payload  # noqa: E402

DEFAULT_TIMEOUT_S = 120.0  # main.py DEFAULTS
LEASE_MULTIPLIER = 5  # lease sits well above a slow-but-alive run, never re-serve it


class DispatchHandler(BaseHTTPRequestHandler):
  server: "DispatchServer"

  def log_message(self, format: str, *args: Any) -> None:
    """Only failures. 16 workers at a run a second buried the campaign log in
    access lines and pushed it into the gigabytes over a long run."""
    status = str(args[1]) if len(args) > 1 else ""
    if not status.startswith("2"):
      super().log_message(format, *args)

  def do_GET(self) -> None:
    if self.path == "/next":
      self._serve_next()
    elif self.path == "/status":
      self._send_json(200, self.server.store.counts())
    else:
      self.send_error(404)

  def do_POST(self) -> None:
    if self.path != "/result":
      self.send_error(404)
      return
    try:
      body = self._read_json()
      report = report_from_payload(body["report"])
      self.server.store.record(body["experiment_id"], report)
    except (KeyError, TypeError, ValueError) as exc:
      self.send_error(400, str(exc))
      return
    self._send_empty(204)

  def _serve_next(self) -> None:
    claimed = self.server.store.claim(self.server.lease_s)
    if claimed is None:
      self._send_empty(204)  # drain signal: the worker exits on 204
      return
    self._send_json(200, claimed_to_payload(claimed))

  def _read_json(self) -> dict[str, Any]:
    length = int(self.headers.get("Content-Length", 0))
    body: dict[str, Any] = json.loads(self.rfile.read(length)) if length else {}
    return body

  def _send_json(self, code: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode()
    self.send_response(code)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def _send_empty(self, code: int) -> None:
    self.send_response(code)
    self.end_headers()


class DispatchServer(HTTPServer):
  """Single-threaded on purpose.

  The store has exactly one writer and does no locking; a ThreadingHTTPServer
  would race two claims onto the same row. ~16 workers at one request every few
  seconds leaves a serial loop mostly idle.
  """

  def __init__(self, address: tuple[str, int], store: Store, lease_s: float) -> None:
    super().__init__(address, DispatchHandler)
    self.store = store
    self.lease_s = lease_s


def parse_args() -> argparse.Namespace:
  p = argparse.ArgumentParser(description=__doc__)
  p.add_argument("--db", default=str(REPO_ROOT / "runs" / "campaign.db"))
  p.add_argument("--host", default="0.0.0.0")
  p.add_argument("--port", type=int, default=8080)
  p.add_argument("--protocols", default="mascot,spdz2k,malicious-shamir",
                 help="comma-separated; crossed with --party-counts")
  p.add_argument("--party-counts", default="3,5,7,9", help="comma-separated")
  p.add_argument("--runs", type=int, default=5000, help="experiments per grid point")
  p.add_argument("--start-seed", type=int, default=0)
  p.add_argument("--timeout-s", type=float, default=DEFAULT_TIMEOUT_S,
                 help="per-run pipeline timeout handed to workers")
  p.add_argument("--lease-s", type=float,
                 help=f"claim lease in seconds (default {LEASE_MULTIPLIER}x --timeout-s)")
  p.add_argument("--rng-seed", type=int, default=0,
                 help="seeds corrupt-set and depth sampling; replays a campaign")
  p.add_argument("--max-depth", type=int, default=40)
  p.add_argument("--combo", default="baseline")
  return p.parse_args()


def plan_from_args(args: argparse.Namespace) -> CampaignPlan:
  return CampaignPlan(
    protocols=parse_protocols(args.protocols.split(",")),
    party_counts=tuple(int(n) for n in args.party_counts.split(",") if n.strip()),
    runs_per_config=args.runs,
    start_seed=args.start_seed,
    timeout_s=args.timeout_s,
    rng_seed=args.rng_seed,
    max_depth=args.max_depth,
    combo=args.combo,
  )


def main() -> None:
  args = parse_args()
  db_path = Path(args.db)
  db_path.parent.mkdir(parents=True, exist_ok=True)

  plan = plan_from_args(args)
  store = Store(db_path)
  # Idempotent: a restart reattaches to a live campaign, it does not clone it.
  inserted = populate(store, plan)
  lease_s = args.lease_s if args.lease_s else args.timeout_s * LEASE_MULTIPLIER

  print(f"db={db_path} grid={len(plan.grid_points)} planned={plan.total_runs} "
        f"inserted={inserted} lease={lease_s:.0f}s", flush=True)
  print(f"serving on {args.host}:{args.port} (/next /result /status)", flush=True)

  DispatchServer((args.host, args.port), store, lease_s).serve_forever()


if __name__ == "__main__":
  main()
