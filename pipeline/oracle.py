"""Oracle: classify a twin-run.

Returns a `Verdict` whose `category` is the discriminator the loop reads:

  caught          a malicious-security check fired, whatever else printed
  inert           mutated output matches honest output
  aborted         mutated aborted due to timeout or crash (exit code -1)
  honest_invalid  honest produced no output; test program unusable
  bug             mutated output differs from honest output

`reason` is the human-readable text for logs / reports.
"""
from __future__ import annotations

from pipeline.config import NeedsOracle
from pipeline.types import PartyOutput, RunResult, Verdict, VerdictCategory


def judge(result: RunResult, config: NeedsOracle) -> Verdict:
  honest_output = _joined_stdout(result.honest_run)
  mutated_output = _joined_stdout(result.mutated_run)

  if not honest_output:
    return _verdict(
      "honest_invalid", "honest produced no output; test program invalid",
      honest_output, mutated_output,
    )
  # Before comparing outputs, not only when there are none. A party that
  # reveals some values and then fails its MAC check has been caught, and
  # judging it on the partial stdout it managed to print first reports the
  # protocol working as a soundness bug.
  if _caught(result.mutated_run, config.spec.catch_signatures):
    return _verdict(
      "caught", "malicious-security check caught the mutation",
      honest_output, mutated_output,
    )
  if not mutated_output:
    category, reason = _diagnose_abort(result.mutated_run)
    return _verdict(category, reason, honest_output, mutated_output)
  if mutated_output == honest_output:
    return _verdict(
      "inert", "mutated output matches honest output",
      honest_output, mutated_output,
    )
  return _verdict(
    "bug", "mutated output differs from honest output",
    honest_output, mutated_output,
  )


def _verdict(
  category: VerdictCategory, reason: str,
  honest_output: str, mutated_output: str,
) -> Verdict:
  return Verdict(
    category=category, reason=reason,
    honest_output=honest_output, mutated_output=mutated_output,
  )


def _joined_stdout(parties: tuple[PartyOutput, ...]) -> str:
  return "".join(p.stdout for p in parties)


def _caught(
  parties: tuple[PartyOutput, ...],
  catch_signatures: tuple[str, ...],
) -> bool:
  return any(sig in p.stderr for sig in catch_signatures for p in parties)


def _diagnose_abort(parties: tuple[PartyOutput, ...]) -> tuple[VerdictCategory, str]:
  if any(p.exit_code == -1 for p in parties):
    return "aborted", "mutated run timed out"
  return "aborted", "mutated run aborted before any output"
