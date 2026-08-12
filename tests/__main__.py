"""`uv run python -m tests` — the whole suite, no framework."""
from __future__ import annotations

from typing import Callable

from tests import test_generation

SUITES: tuple[tuple[str, Callable[[], None]], ...] = (
  ("test_generation", test_generation.run),
)


def main() -> None:
  failed: list[str] = []
  for name, suite in SUITES:
    try:
      suite()
    except AssertionError as failure:
      failed.append("%s: %s" % (name, failure))
  if failed:
    for line in failed:
      print("FAILED " + line)
    raise SystemExit(1)
  print("all suites passed")


main()
