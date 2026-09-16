"""Campaign dispatcher: hands experiments to workers over HTTP, records results.

  GET  /next     200 + claimed experiment, or 204 once the campaign is drained
  POST /result   {"experiment_id", "report"}; 200 + verdict counts so far
  GET  /status   200 + verdict counts so far

Single-threaded on purpose: the store has one writer and no locking, and a
handful of workers at one request every few seconds leaves a serial loop idle.

  python -m pipeline.dispatch --db runs/campaign.db --runs 5000
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable

from pipeline.campaign import CampaignPlan, parse_protocols, populate
from pipeline.store import Store
from pipeline.wire import claimed_to_payload, report_from_payload

LEASE_MULTIPLIER = 5  # a lease sits well above a slow-but-alive run

Route = tuple[str, str]


@dataclass(frozen=True)
class Serve:
  """What the server needs besides the plan."""
  db: Path
  host: str
  port: int
  lease_s: float


class DispatchHandler(BaseHTTPRequestHandler):
  def __init__(self, *args: Any, store: Store, lease_s: float, **kwargs: Any) -> None:
    self.store = store
    self.lease_s = lease_s
    super().__init__(*args, **kwargs)

  def do_GET(self) -> None:
    self._route("GET")

  def do_POST(self) -> None:
    self._route("POST")

  def _route(self, method: str) -> None:
    handler = self._routes().get((method, self.path))
    if handler is None:
      self.send_error(HTTPStatus.NOT_FOUND)
      return
    handler()

  def _routes(self) -> dict[Route, Callable[[], None]]:
    return {
      ("GET", "/next"): self._serve_next,
      ("GET", "/status"): self._serve_status,
      ("POST", "/result"): self._record_result,
    }

  def _serve_next(self) -> None:
    claimed = self.store.claim(self.lease_s)
    if claimed is None:
      self.send_response(HTTPStatus.NO_CONTENT)
      self.end_headers()
      return
    self._send_json(claimed_to_payload(claimed))

  def _serve_status(self) -> None:
    self._send_json(self.store.counts())

  def _record_result(self) -> None:
    try:
      body = self._read_json()
      self.store.record(body["experiment_id"], report_from_payload(body["report"]))
    except (KeyError, TypeError, ValueError) as exc:
      self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
      return
    self._send_json(self.store.counts())

  def _read_json(self) -> dict[str, Any]:
    length = int(self.headers.get("Content-Length", 0))
    body: dict[str, Any] = json.loads(self.rfile.read(length)) if length else {}
    return body

  def _send_json(self, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode()
    self.send_response(HTTPStatus.OK)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
    """Failures only; successes at one request a second would bury the log."""
    if isinstance(code, int) and HTTPStatus.OK <= code < HTTPStatus.MULTIPLE_CHOICES:
      return
    super().log_request(code, size)


def parse(argv: list[str] | None = None) -> tuple[CampaignPlan, Serve]:
  p = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  grid = p.add_argument_group(
    "campaign", "every protocol at every party count; --runs experiments per point")
  grid.add_argument("--protocols", default="mascot,spdz2k,malicious-shamir",
                    help="comma-separated protocol names")
  grid.add_argument("--party-counts", default="3,5,7,9",
                    help="comma-separated party counts")
  grid.add_argument("--runs", type=int, default=5000, help="experiments per grid point")
  grid.add_argument("--start-seed", type=int, default=CampaignPlan.start_seed,
                    help="first seed; seeds count up from here across the grid")
  grid.add_argument("--timeout-s", type=float, default=CampaignPlan.timeout_s,
                    help="per-run pipeline timeout handed to workers")
  grid.add_argument("--rng-seed", type=int, default=CampaignPlan.rng_seed,
                    help="seeds the corrupt-set and depth draws; same value replays")
  grid.add_argument("--max-depth", type=int, default=CampaignPlan.max_depth,
                    help="upper bound for a grid point's expression depth")
  grid.add_argument("--combo", default=CampaignPlan.combo,
                    help="label for the check-site combination under test")
  serve = p.add_argument_group("serve")
  serve.add_argument("--db", type=Path, default=Path("runs/campaign.db"))
  serve.add_argument("--host", default="0.0.0.0")
  serve.add_argument("--port", type=int, default=8080)
  serve.add_argument("--lease-s", type=float,
                     help=f"claim lease in seconds; default {LEASE_MULTIPLIER}x --timeout-s")
  args = p.parse_args(argv)
  plan = CampaignPlan(
    protocols=parse_protocols(args.protocols.split(",")),
    party_counts=tuple(int(n) for n in args.party_counts.split(",") if n.strip()),
    runs_per_point=args.runs,
    start_seed=args.start_seed,
    timeout_s=args.timeout_s,
    rng_seed=args.rng_seed,
    max_depth=args.max_depth,
    combo=args.combo,
  )
  lease_s = args.lease_s if args.lease_s else plan.timeout_s * LEASE_MULTIPLIER
  return plan, Serve(db=args.db, host=args.host, port=args.port, lease_s=lease_s)


def main(plan: CampaignPlan, serve: Serve) -> None:
  serve.db.parent.mkdir(parents=True, exist_ok=True)
  store = Store(serve.db)
  inserted = populate(store, plan)
  print(f"db={serve.db} grid={len(plan.grid_points)} planned={plan.total_runs} "
        f"inserted={inserted} lease={serve.lease_s:.0f}s", flush=True)
  print(f"serving on {serve.host}:{serve.port}", flush=True)
  handler = partial(DispatchHandler, store=store, lease_s=serve.lease_s)
  HTTPServer((serve.host, serve.port), handler).serve_forever()


if __name__ == "__main__":
  main(*parse())
