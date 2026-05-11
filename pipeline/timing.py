"""Around-advice timing.

`with Timer() as t:` records start in `__enter__`, end in `__exit__`,
and exposes `elapsed_ms` as a derived `@property`.
"""
from __future__ import annotations

import time
from types import TracebackType


class Timer:
  def __enter__(self) -> "Timer":
    self._start = time.monotonic()
    return self

  def __exit__(
    self,
    exc_type: type[BaseException] | None,
    exc: BaseException | None,
    tb: TracebackType | None,
  ) -> None:
    self._end = time.monotonic()

  @property
  def elapsed_ms(self) -> int:
    return int((self._end - self._start) * 1000)
