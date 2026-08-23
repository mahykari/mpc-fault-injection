# PROGRESS

## Fix when merging to master

Running list. These are things this branch changed or uncovered that master
needs handled at merge time, not things already done here.

- **Runtime prime does not match the compile prime.** `pipeline/protocols.py`:
  `Prime.runtime_args` passes `-P <2^127-1>` while `Prime.compile_args` returns
  `[]`, so every program is compiled for MP-SPDZ's default prime and executed
  under a 127-bit one. Unchanged from master, so every campaign to date ran this
  way, and it is benign in a clean run directory. Pick one prime and pass it to
  both sides. Detail under "Patched binary" below.
- **python-circil was replaced with the upstream clone.** Master's `pipeline/`
  does not run against it unmodified: `FuzzerConfig.enable_fixed_size_array` is
  now `enable_array`, `array_types_for_fixed_size_array` is
  `array_element_types`, and `Custom.constructor()` is a `@staticmethod`
  returning a templated spec rather than an instance method.
- **MP-SPDZ moved 0.4.2 to 0.4.3.** `containers/Containerfile`,
  `containers/build.sh` and `patches/mpspdz/README.md` are bumped here. Patch
  0001 applies to 0.4.3 with a 16-line offset. Confirm before the merge lands.
- **Two new Config defaults to agree on.** `injection_layer` defaults to
  `"bytecode"` so the field family keeps working; `mutation_kind` defaults to
  `"inject"`. Decide what master should ship.

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

## Step 1 and 2 — translator, source-layer injector (2026-08-23)

MP-SPDZ v0.4.3 is now on disk at `MP-SPDZ/` (gitignored). There was no copy
to symlink: the master checkout has none either. Note the Containerfile still
builds 0.4.2 and `patches/mpspdz/` is written against a clean 0.4.2 tree, so
local and container disagree until one moves.

### Translator

`pipeline/translator.py` rewritten. Expression rendering moved from a single
text buffer to a value stack, because a matrix literal is two statements rather
than an expression: `Matrix(r, c, sint)` is uninitialised on construction and
needs a following `assign_all`. A matrix-valued node emits statements and pushes
the name of the temporary it built. Field arithmetic still renders inline.

API, read out of `MP-SPDZ/Compiler/types.py` rather than guessed:
`Matrix(rows, columns, value_type)` 7758, `assign_all` 6851, `__add__` 7109,
`dot` 7201, `transpose` 7501, `reveal_nested` 7655.

### Source-layer injector

- `pipeline/types.py` — `InjectionLayer = Literal["bytecode", "source"]`.
- `pipeline/config.py` — `Config.injection_layer`, default `"bytecode"`.
- `pipeline/source_injector.py` — rewrites the CircIL AST, translates and
  compiles the mutated twin separately. Rule set is currently the
  rearrangements, so this is the control arm until injection rules land.
- `pipeline/__init__.py` — `_INJECTORS` selects on the typed field.

The bytecode injector is retired, not deleted: still wired, still type-checked,
still the default, and it keeps serving the field family.

`Injector._check_sync_invariant` no longer raises. A diverged signature is
printed and the run continues.

### Verified

Suite is 24 checks across three modules, `uv run mypy` clean over 32 files.
`test_translation` compiles honest and rewritten circuits against real MP-SPDZ
and reports skipped when `MP-SPDZ/` is absent.

End-to-end, matrix family, source injection, mascot n=2, seed 3: the honest twin
runs and reveals correct matrices.

```
out0: [[219416777170372848, ...4 wide], ...3 rows]
out2: [[2652866328, 2652866328], ...3 rows]
```

### Blocked on the patched binary

The mutated twin aborts before producing output. Not a defect in this work: the
established field family on the bytecode injector aborts identically on this
machine, same seed. The local `MP-SPDZ/bin/Linux-amd64/` binaries are stock, and
twin runs need `patches/mpspdz/0001-noop-check-program.patch`, which only exists
via the container build. `./containers/build.sh pipeline` is the next action and
it is run by hand.

## Unit 3 — injection rules (2026-08-23)

### Done

- `pipeline/rewrite/donors.py` — donor search. `donors_of_type(circuit,
  before, wanted)` returns in-scope nodes of a type in a stable pre-order;
  `pick_donor` takes one with a seeded RNG or returns None. Scope is
  deliberately conservative: a donor is admissible only when every identifier
  it mentions is a circuit input or the target of an earlier assignment, so
  nothing reaching a `let`-bound name is ever spliced. That rejects donors that
  would in fact be fine, which is the cheap direction to be wrong in.
- `pipeline/rewrite/inject.py` — three rules. `matmul-add-donor` is
  `(matmul ?a ?b) -> (matmul (add ?a ?r) ?b)`; `field-bump-donor` is the port of
  the bump gadget, `a -> (a + r)`; `field-signflip` is the port of the sign-flip
  gadget, `a -> (a * -1)`.
- `pipeline/types.py` / `config.py` — `MutationKind = Literal["rearrange",
  "inject"]`, default `"inject"`. `rearrange` keeps the control arm reachable.
- `pipeline/source_injector.py` selects the mutator on that typed field.

### Decision: injections are not CircIL patterns

Unit 2's rules are patterns. These are not, and that is deliberate. A rewrite
pattern can only build a term out of what the match bound or what `$r`
synthesises, and a synthesised literal is exactly what an injected operand must
not be. Matching and construction therefore both live in `inject.py`, so a rule
has one mechanism rather than two.

`field-signflip`'s `-1` stays a literal: it is the operator, not an injected
operand, and it is what `mulsi r, r, -1` did.

### Verified

```
  ok   40 injected circuits typecheck and translate
  ok   injections change the circuit (38/40)
  ok   matmul-add-donor fired (4)
  ok   field-bump-donor fired (17)
  ok   field-signflip fired (40)
  ok   same seed injects identically
  ok   every donor is in scope at its splice point
```

Suite is 31 checks over four modules. `uv run mypy` clean over 35 files.

## Patched binary, and two things it turned up (2026-08-23)

`./containers/build.sh patched` now builds MP-SPDZ 0.4.3 (Containerfile and
build.sh bumped to match what is on disk; patch 0001 applies to 0.4.3 with a
16-line offset). Binaries are in `MP-SPDZ/bin/Linux-amd64-patched/`.

**1. The runtime prime does not match the compile.** `Prime.runtime_args` passes
`-P <M127>` but `Prime.compile_args` is empty, so the program is compiled for
MP-SPDZ's default prime and run under a 127-bit one. This is unchanged from
master, so every previous campaign ran the same way.

It is an asymmetry worth tidying, but it is **not** the failure originally
written up here. A clean-room A/B, fresh `runs_root`, both stock and patched
binaries, runs the honest twin correctly with `-P` in place. The
`honest_invalid` reported earlier came from a polluted run directory: leftover
`Mascot-Secrets-p-128-*` files from manual experiments run *without* `-P` become
a stale cache under `-P`, which trips a MAC failure and then an assert in the
cache-cleanup path, `unlink(filename.c_str()) == 0` at `Protocols/MAC_Check.hpp:165`.

**2. `mutated/Player-Data` is empty.** Also written up here as a MAC-key
mismatch, also wrong. `OT/MascotMacKey.hpp:29` `read_or_generate` reads *that
party's own* cached share or generates a fresh one and runs OT base setup with
its peers. Shares are per-party by design; an empty directory is a supported
path. Both parties printed that warning in runs that produced correct output.

**What is actually still blocking: preprocessing volume.** Diagnosed
2026-08-23. The mutated twin aborts because honest and mutated parties disagree
about how much offline material the program needs:

```
Fatal error in OT thread: Bad receive buffer size.
  Size transmitted: 175104 bytes
  Size of buffer:   178176 bytes
```

MASCOT sizes its offline phase to the program it is running. Two parties running
two different programs size it differently, and the channel desynchronises
before any online computation happens. Patch 0001 gets past the fingerprint
check; this is the next wall behind it.

The bytecode gadgets never hit this. `addsi` / `mulsi` take an immediate
operand and consume no triples, so a bump or a sign flip left the preprocessing
volume byte-identical. That property was doing more work than the note in
`single_variable_bump.py` lets on. A source-level mutation has no such
guarantee: it changes the program, and the program is what the offline phase is
sized from.

Two consequences. Any source-level mutation has to be preprocessing-neutral, or
the twin design needs the offline phase pinned independently of the program.
Neither is a patch to `check_program`.

A second, smaller asymmetry sits in front of it: the executor runs the honest
twin first, which populates `honest/Player-Data` with an OT secrets cache. The
mutated twin then has one party reading a cache and skipping base-OT setup while
the other regenerates it interactively, so they are in different phases and the
honest side reports `Timed out waiting for peer`. Seeding `mutated/Player-Data`
from `honest/` clears that one and exposes the buffer-size error above.

The abort is pre-existing and independent of the source-level work: the field
family on the bytecode injector hits it too, same seed.
