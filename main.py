"""Pipeline entrypoint.

`uv run python main.py` must always succeed. If it doesn't,
the pipeline invariant is broken (BLUEPRINT.md).
"""
from __future__ import annotations

from pipeline import run_pipeline
from pipeline.types import Seed


def main() -> None:
  report = run_pipeline(Seed(value=42))
  print()
  print("=== Report ===")
  for field, value in report.__dict__.items():
    print(f"  {field}: {value}")


if __name__ == "__main__":
  main()
