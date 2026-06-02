"""Program Generator: drives python-circil's SimpleCircuitFuzzer.

The fuzzer's surface is huge (arrays, lambdas, ternaries, generics,
custom functions); we strip it to Field-only arithmetic over the
three op gadgets — MUL, SUB, ADD — so the translator below stays
small and downstream MP-SPDZ compilation is predictable.
"""
from __future__ import annotations

import pipeline.circil as _circil_path_setup  # noqa: F401
from random import Random

import circil.ir.types as IRType  # type: ignore[import-not-found]
from circil.fuzzer.builtin_operators import Builtins  # type: ignore[import-not-found]
from circil.fuzzer.config import FuzzerConfig  # type: ignore[import-not-found]
from circil.fuzzer.simple import SimpleCircuitFuzzer  # type: ignore[import-not-found]

from pipeline.config import NeedsGenerator
from pipeline.types import CircilProgram

# CircIL bounds emitted constants by this modulo. Kept small (Mersenne
# prime 2^31 - 1) so constants comfortably fit MP-SPDZ's default field
# and the translator can emit them as plain `sint(<int>)` literals.
FIELD_MODULO = 2**31 - 1


def _fuzzer_config(config: NeedsGenerator) -> FuzzerConfig:
  return FuzzerConfig(
    max_expression_depth=config.expression_depth,
    min_assertions=0, max_assertions=0,
    min_circuit_input_signals=2, max_circuit_input_signals=10,
    min_circuit_output_signals=1, max_circuit_output_signals=5,
    probability_boundary_value=0.1,
    disable_field_modulo_boundary_value=True,
    ternary_expression_types=[],
    input_signal_types=[IRType.Field],
    output_signal_types=[IRType.Field],
    allowed_generic_concrete_types=[IRType.Field],
    enable_fixed_size_array=False,
    max_lambda_depth=0,
    probability_weight_let=config.let_probability,
    custom_functions=[Builtins.MUL, Builtins.SUB, Builtins.ADD],
  )


def generate_program(config: NeedsGenerator) -> CircilProgram:
  rng = Random(config.seed.value)
  circuit = SimpleCircuitFuzzer(FIELD_MODULO, rng, _fuzzer_config(config)).run()
  print(
    f"[generator] CircIL circuit (seed={config.seed.value}, "
    f"inputs={len(circuit.inputs)}, "
    f"outputs={len(circuit.outputs)}, "
    f"statements={len(circuit.statements)})"
  )
  return CircilProgram(circuit=circuit)
