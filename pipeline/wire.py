"""JSON codec on the worker/dispatcher boundary.

Both sides import these four functions, so the payload shape is defined in one
place. Tuples in `types.py` go out as JSON lists and must come back as tuples;
`dataclasses.asdict` + `json.loads` would silently return lists and leave the
mismatch to whatever unpacks them later.
"""
from __future__ import annotations

from typing import Any

from pipeline.store import ClaimedExperiment, ExperimentConfig
from pipeline.types import InjectionRecord, Report, Verdict


def claimed_to_payload(claimed: ClaimedExperiment) -> dict[str, Any]:
  config = claimed.config
  return {
    "experiment_id": claimed.experiment_id,
    "seed": claimed.seed,
    "config": {
      "protocol": config.protocol,
      "n_parties": config.n_parties,
      "corrupt_set": sorted(config.corrupt_set),
      "expression_depth": config.expression_depth,
      "combo": config.combo,
      "timeout_s": config.timeout_s,
    },
  }


def claimed_from_payload(payload: dict[str, Any]) -> ClaimedExperiment:
  config = payload["config"]
  return ClaimedExperiment(
    experiment_id=payload["experiment_id"],
    seed=payload["seed"],
    config=ExperimentConfig(
      protocol=config["protocol"],
      n_parties=config["n_parties"],
      corrupt_set=frozenset(config["corrupt_set"]),
      expression_depth=config["expression_depth"],
      combo=config["combo"],
      timeout_s=config["timeout_s"],
    ),
  )


def report_to_payload(report: Report) -> dict[str, Any]:
  return {
    "fault": {
      "tape_index": report.fault.tape_index,
      "party_ids": list(report.fault.party_ids),
      "gadget_kinds": list(report.fault.gadget_kinds),
      "details": list(report.fault.details),
    },
    "verdict": {
      "category": report.verdict.category,
      "reason": report.verdict.reason,
      "honest_output": report.verdict.honest_output,
      "mutated_output": report.verdict.mutated_output,
    },
    "duration_ms": report.duration_ms,
    "combo": report.combo,
    "protocol": report.protocol,
    "n_parties": report.n_parties,
  }


def report_from_payload(payload: dict[str, Any]) -> Report:
  fault = payload["fault"]
  verdict = payload["verdict"]
  return Report(
    fault=InjectionRecord(
      tape_index=fault["tape_index"],
      party_ids=tuple(fault["party_ids"]),
      gadget_kinds=tuple(fault["gadget_kinds"]),
      details=tuple(fault["details"]),
    ),
    verdict=Verdict(
      category=verdict["category"],
      reason=verdict["reason"],
      honest_output=verdict["honest_output"],
      mutated_output=verdict["mutated_output"],
    ),
    duration_ms=payload["duration_ms"],
    combo=payload["combo"],
    protocol=payload["protocol"],
    n_parties=payload["n_parties"],
  )
