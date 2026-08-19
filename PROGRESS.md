# PROGRESS

## Unit 1 — Matrix type, spec table, repeatability suite (2026-08-12)

### Done

- `pipeline/matrix.py` — `Matrix(IRType.Custom)` with the shape folded into
  `Custom.name` (`Matrix[2x3]`); `DIMS=(2,3)`, `SHAPES` = the 4 products.
  `matrix_specs()` returns 16 concrete specs: 8 `matmul` (DIMS^3), 4 `madd`,
  4 `transpose`. `matrix_fill` is reached per-instance via `constructor()`,
  not registered.
- `pipeline/circil_ir.py` — node-poke helpers: `call`, `is_call`, `type_of`
  (guarded), `shape_of`, `is_field`, `integer`.
- `pipeline/check.py` — `CircuitChecker(IRWalker)` + `check_circuit` (call
  count) and `call_names` (per-name Counter). Shape rules per function name
  in a `CALL_RULES` dispatch table; identifier scope tracked so a splice out
  of scope raises.
- `pipeline/generator.py` — `_matrix_fuzzer_config` alongside the untouched
  `_fuzzer_config`; `_CONFIG_BUILDERS` selects on the new typed Config field.
- `pipeline/types.py` — `ProgramFamily = Literal["field", "matrix"]`.
- `pipeline/config.py` — `Config.program_family` (default `"field"`),
  `NeedsGenerator.program_family`.
- `tests/` — `support.py` (`matrix_config`, `expect`, the two hand-built
  circuits), `test_generation.py`, `__main__.py`. Plain module, no framework.
- `pyproject.toml` — mypy `files` gains `tests`.

Zero edits under `python-circil/`.

### Verified

`uv run python -m tests`:

```
test_generation
  ok   matrix_specs has 16 concrete specs
  ok   every spec's result shape follows from its operands
  ok   200 generated circuits typecheck
  ok   batch contains matmul (229)
  ok   batch contains madd (119)
  ok   batch contains transpose (104)
  ok   same seed generates an identical circuit twice
  ok   hand-built transpose of product typechecks
  ok   hand-built double transpose typechecks
all suites passed
```

`uv run mypy` → `Success: no issues found in 26 source files`.

Output is byte-identical under `PYTHONHASHSEED` 0 / 1 / 12345 (md5 of the
full run matched three times).

### Ambiguities resolved

- **Depth for the matrix family.** Design says `max_expression_depth=4`, but
  `Config.expression_depth` (default 20) is a knob. Resolved: hard-coded as
  `MATRIX_EXPRESSION_DEPTH = 4` in `generator.py`; the matrix family ignores
  `config.expression_depth` entirely. Revisit if the knob is wanted per family.
- **Per-name call counts.** `check_circuit -> int` per the design, so the
  batch counter needed a second accessor rather than a second walker:
  `call_names(circuit) -> Counter[str]` reuses `CircuitChecker`.
- **Call checks dispatch.** Written as a `CALL_RULES` name→predicate table
  rather than the if/elif chain the design sketched. Same rules.
- **Test harness shape.** `run() -> None` as designed; failures raise
  `CheckFailed(AssertionError)` and `tests/__main__.py` collects and exits 1.
  Per-check lines print as they run.
- **`tests/__main__.py` wires only `test_generation`.** `test_rules` does not
  exist yet; Unit 2 adds a row to `SUITES`.
- **Hand-built fixtures.** Design lists them under Unit 1's `support.py` but
  they are Unit 2 inputs. Kept, and `test_generation` asserts `check_circuit`
  accepts both, so they are not dead code.
- **Generator stdout.** `generate_program` prints a line per circuit; the
  200-circuit batch redirects stdout so the check lines stay readable.
- **Batch counts differ slightly from the design's measurements** (design:
  300 circuits, matmul 232 / madd 138 / transpose 110; here: 200 circuits,
  229 / 119 / 104). Expected — different batch size and input-signal bounds
  (2..10, matching `_fuzzer_config`, vs the probe's 2..6).

### Not done (out of scope for Unit 1)

Units 2 and 3 (`pipeline/rewrite/`). Translator arms for
`matmul`/`madd`/`transpose`/`matrix_fill` — `pipeline/translator.py` still
handles `+ - *` only, so matrix circuits cannot reach MP-SPDZ yet.

## Unit 1 redone — value-parameterized Matrix (2026-08-15)

python-circil was replaced with a real clone of
`Rigorous-Software-Engineering/python-circil` (`main`); the old vendored copy
sits at `python-circil.old/`. The new circil has a general template system, so
the enumeration above is gone.

### Done

- `pipeline/matrix.py` rewritten against `circil.ir.templates`. `Matrix` is a
  `Custom` with `rows`/`cols` value parameters (`None` = unspecified, matches
  any). `MatrixTemplate` implements `resolve_type` / `extract_mappings` /
  `signature_key` / `free_variables`. `_RequestMatrix` carries a `range` for a
  dimension the solver has not pinned yet, mirroring `_RequestSizedString`.
- `matrix_specs()` is now 3 shape-polymorphic specs, not 16 concrete ones:
  `matmul` declares `m,k,n` and takes `Matrix<m,k>`, `Matrix<k,n>` -> `Matrix<m,n>`;
  `add` declares `m,n`; `transpose` swaps to `Matrix<n,m>`.
- `Custom.constructor()` is a `@staticmethod` in the new circil, so
  `matrix_fill` became a templated spec with its own `rows`/`cols` parameters
  instead of an instance method baking in a fixed shape.

### Verified

`uv run python -m tests`:

```
  ok   matrix_specs has 3 shape-polymorphic specs
  ok   every spec's result shape follows from its operands
  ok   200 generated circuits typecheck
  ok   batch contains matmul (178)
  ok   batch contains add (148)
  ok   batch contains transpose (151)
  ok   same seed generates an identical circuit twice
  ok   hand-built transpose of product typechecks
  ok   hand-built double transpose typechecks
all suites passed
```

`uv run mypy` -> `Success: no issues found in 31 source files`.

Shape variety over 60 circuits: all 16 shapes in 1..4 x 1..4 appear, none
dominating (top: (1,3) 120, (3,4) 120, (1,1) 103). The value parameters really
do vary; they are not collapsing to one shape.

### Ambiguities resolved

- **Dimension bounds.** Not specified. Chose `MIN_DIM=1`, `MAX_DIM=4`, enforced
  by a `RangeConstraint` per parameter, because every circuit becomes an MP-SPDZ
  program and matmul costs O(m*k*n) secret multiplications.
- **`add` vs `madd`.** The first pass named it `madd` to dodge the builtin `+`.
  Renamed to `add` per the brief, since the injection rule is written
  `(matmul (add ?a ?r) ?b)`. No collision: the field builtin is `+`.
- **Literal dimension against a solver range.** circil's `SizedStringTemplate`
  randomises within the range in that branch; that contradicts the literal, so
  `_extract_dim` returns the literal after checking it falls in the range.
- **Type hint registration.** `BaseParser.register_templated_type` (a
  `MatrixHint`) is what lets `matrix` appear in rewrite *patterns*. Not needed to
  generate, so it is left for Unit 2.

### Carried over, not mine

`pipeline/config.py` (`NeedsRewriter`) and `pipeline/rewrite/` are leftovers
from the Unit 2 that was stopped mid-write; both are excluded from this commit.
`pipeline/rewrite/rearrange.py` got a one-word `MADD` -> `ADD` fix only so
`mypy` stays green.

### Known footgun

`import pipeline.circil` puts `python-circil/` at the front of `sys.path`, and
python-circil ships a top-level `tests` package. Import our `tests.*` first or
it gets shadowed. `uv run python -m tests` is unaffected.

## Unit 2 — rearrangement rules as CircIL patterns (2026-08-19)

Rules are CircIL `Rule(name, match, rewrite)` patterns, not the hand-rolled
`matches`/`build` classes from the stopped run. Those files are deleted, not
reduced: `engine.py`, `rearrange.py`, `sites.py`, `types.py` are gone. The
`SiteIndex` scope machinery went with them, so Unit 3 will need its own scope
test wherever `?r` sourcing lands.

No circil patch was needed after all. `BaseParser.register_templated_type` is a
plain static method mutating a class dict, so `pipeline.matrix.MatrixHint`
registers itself at import time from our side.

### Done

- `pipeline/matrix.py` gains `MatrixHint(TemplatedTypeHint)`, modelled on the
  built-in `ArrayHint`: two VALUE slots, each a literal or a `?name` bound in
  `lookup`. Matching binds a dimension, the rewrite side reads it back, which
  is how a rule states a transposed shape without computing types itself.
- `pipeline/rewrite/rules.py` — `transpose-of-product`, `double-transpose-elim`,
  `add-commute`.
- `pipeline/rewrite/engine.py` — `rewrite_circuit(circuit, seed, amount)` over
  `RuleBasedRewriter`; the library owns the walk and splice.
- `tests/test_rules.py`, wired into `tests/__main__.py`.

### Verified

```
test_rules
  ok   transpose-of-product matches generated output (14 sites)
  ok   double-transpose-elim matches generated output (6 sites)
  ok   add-commute matches generated output (104 sites)
  ok   120 rewritten circuits typecheck
  ok   rules actually fired (173 applications)
  ok   same seed rewrites identically
```

`uv run mypy` -> `Success: no issues found in 30 source files`.

### The bug this nearly shipped with

The first version of these rules matched the hand-built fixtures in
`tests/support.py` and *nothing* the generator emits. Every check passed: the
rules fired on fixtures, and "60 rewritten circuits typecheck" was true because
zero rewrites happened. Only an explicit "rules actually fired" count caught it.

Cause: a generated call carries **template arguments**, the resolved
`with_generic_value` parameters, and `process_call_expression` requires
`len(templates) == len(node.function.template_parameters)`. A pattern omitting
the chevron list matches no generated call. Hand-built fixtures have none, so
they matched. `(add<?m, ?n>:?t<matrix> ?a ?b)` is the correct form.

The tests now measure site counts against generated circuits for this reason.

### Left dirty

`pipeline/config.py` still carries an unused `NeedsRewriter` view from the
stopped run. `git checkout --` is on the deny list, so it is uncommitted rather
than reverted.
