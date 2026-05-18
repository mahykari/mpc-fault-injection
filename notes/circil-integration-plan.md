# CircIL integration plan

Branch parked off `master`; resume after `pipeline-scaffold` merges.
Goal: replace the `Generator` + `Translator` stubs in `pipeline/generator.py`
with real seed-driven CircIL fuzzing + a CircIL→MP-SPDZ DSL translator.

## Library read

`./python-circil/` (gitignored, SSH clone). The library carries a heavy
type system (Field, Bool, SizedInteger, n-d Array, Union, Generic,
Function w/ closures, Custom) and matching fuzzer machinery (template
resolution, constraint solving, let-rewriting, lambda generation). For
MPC fuzzing we want a tiny slice: Field-only arithmetic, no arrays, no
lambdas, no assertions, no ternaries.

Surface that matters:
- `circil.fuzzer.simple.SimpleCircuitFuzzer(field_modulo, Random, FuzzerConfig).run() → Circuit` — only concrete fuzzer.
- `Circuit` = `name`, `field_modulo`, `input_signals: [Identifier]`, `output_signals: [Identifier]`, `statements: [Statement]`. Clean dataclass-ish AST.
- `circil.fuzzer.config.FuzzerConfig` — the knob to suppress unwanted features.
- `tests/end2end/python_translation.py:PythonTranslation` — reference `IRWalker` translating Circuit → plain Python. **Not** an MP-SPDZ translator; we write our own, but crib the shape.

## `pipeline/types.py` change

```python
# was
@dataclass(frozen=True)
class CircilProgram:
  source: str

# becomes
@dataclass(frozen=True)
class CircilProgram:
  circuit: Any = field(repr=False)  # circil.ir.node.Circuit, no stubs
```

Mirrors how `MpspdzProgram` already wraps `Compiler.program.Program` as
`Any`. AST in memory, no serialize/re-parse round-trip.

## Generator (`pipeline/generator.py:generate_program`)

```python
from random import Random
import circil.ir.types as IRType
from circil.fuzzer.simple import SimpleCircuitFuzzer
from circil.fuzzer.config import FuzzerConfig
from circil.fuzzer.builtin_operators import Builtins

BN254 = 21888242871839275222246405745257275088548364400416034343698204186575808495617

cfg = FuzzerConfig(
  max_expression_depth=3,
  min_assertions=0, max_assertions=0,
  min_circuit_input_signals=2, max_circuit_input_signals=4,
  min_circuit_output_signals=1, max_circuit_output_signals=2,
  probability_boundary_value=0.1,
  disable_field_modulo_boundary_value=True,
  ternary_expression_types=[],
  input_signal_types=[IRType.Field],
  output_signal_types=[IRType.Field],
  allowed_generic_concrete_types=[IRType.Field],
  enable_fixed_size_array=False,
  max_lambda_depth=0,
  custom_functions=Builtins.binary_operations(2),  # +, -, *
)
rng = Random(config.seed.value)
circuit = SimpleCircuitFuzzer(BN254, rng, cfg).run()
return CircilProgram(circuit=circuit)
```

Field modulo: BN254 is arbitrary — CircIL only uses it to bound
constants. MP-SPDZ reinterprets in its own field on the translator side.

## Translator (`pipeline/generator.py:translate_to_mpspdz`)

New `MpspdzTranslation(IRWalker)` modeled on `PythonTranslation`. Emits
MP-SPDZ Python DSL.

- Input signals → baked literals: `name = sint(<seed-derived int>)`.
  Skips `Input-P<n>` plumbing — twin-run only needs determinism, and
  seed already gives us that.
- `Assignment(lhs, rhs)` → `lhs = <rhs>`.
- Expressions:
  - `Integer(v)` → `v`
  - `Identifier(name)` → name
  - `CallExpression(op, [a, b])` for `+`, `-`, `*` → `(<a>) op (<b>)`
  - Anything else → raise; the FuzzerConfig above should make it unreachable.
- Output signals: `print_ln('out_i: %s', out_i.reveal())` for each.

## Risks

- `min_assertions=0`: validator allows it (`validate_positive` is the
  only check), but the fuzzer hasn't been exercised with zero budget.
  If it explodes, set `min_assertions=1` and have the translator drop
  assertions instead.
- `SingleVariableBumpTemplate` anchors on the first LDSI on tape 0.
  Baked `sint(literal)` inputs compile to LDSIs, so the anchor should
  survive — verify empirically on first run.
  - Verified the anchor survives, but it lands on `in0`'s LDSI, which
    is dead for most generated programs. Concrete case (seed=100,
    current generator config): outputs use `in3` and constants, so
    bumping `in0` produces no divergence. Honest and mutated twins
    both print:
    ```
    in0 = sint(1)
    in1 = sint(2)
    in2 = sint(3)
    in3 = sint(4)
    let_var_00000 = sint(1192711701)
    out0 = ((sint(1801533470) - (sint(745186389) * in3)) * let_var_00000)
    out1 = sint(805519004)
    out2 = sint(266488293)
    ```
    Identical output ≠ soundness bug; the mutation just hit a dead
    register. Fix shape: live-path analysis from each OPEN to restrict
    anchor selection to writers on the def-use closure. Same redirect-
    and-bump shape extends to `mulsi` / `MUL` result / TRIPLE / SQUARE /
    DABIT, which is where MASCOT's malicious-only verification lives.
- `disable_field_modulo_boundary_value=True` because emitting a literal
  equal to MP-SPDZ's field modulo is meaningless.

## Future directions

- Re-enable ternary (`ternary_expression_types=[IRType.Field]`). On secret operands MP-SPDZ compiles it to a MUX (mul-based selection) — exercises the translator beyond straight-line arithmetic and lands on a malicious-vs-semi-honest delta (the mul).

## Pipeline invariants to preserve

- `uv run python main.py` end-to-end on the new generator.
- `uv run mypy` green. `circil.*` has no stubs → expect `# type: ignore`
  on imports or a module-level `mypy: ignore-errors` in `generator.py`.
