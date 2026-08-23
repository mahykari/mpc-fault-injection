# Matrix source-level fuzzing: plan to first end-to-end run

Status date: 2026-08-19. Branch `matrix-rewrites`, HEAD `a2f1dec`.

## Where things stand

Working:

- The generator emits matrix circuits. `matmul`, `add`, `transpose` and
  `matrix_fill` are value-parameterized specs; dimensions are solved per call
  site and range over 1..4.
- Rearrangement rules run at source level as CircIL patterns. Over 120
  generated circuits: 173 rule applications, all results typecheck, same seed
  reproduces the same rewrite.

Not working:

- No matrix circuit has reached MP-SPDZ. `pipeline/translator.py` handles
  `+ - *` and raises on anything else.
- MP-SPDZ is not on disk in this worktree or the main repo. It exists only
  inside the `localhost/mpspdz-pipeline` podman image, built from source at
  image build time.

## Step 1. Translator arms for the matrix ops

File: `pipeline/translator.py`.

Today it is an `EmptyVisitor` subclass that composes one expression string per
statement into a buffer, flushes it at each `Assignment`, and bakes each input
signal as a scalar `sint(index + 1)`.

Changes:

- Matrix-typed input signals. A matrix input cannot be one `sint(...)` literal,
  so input emission becomes a shape-aware fill rather than a single expression.
- `matrix_fill(v)` to a matrix whose entries are all `v`.
- `add(a, b)` to element-wise addition.
- `matmul(a, b)` to MP-SPDZ's matrix product.
- `transpose(a)` to MP-SPDZ's transpose.
- Output emission reveals matrix entries rather than one scalar.

Structural change to expect: the current design assumes every expression is a
single inline string. Matrix construction needs statements, not expressions, so
the visitor will likely need to emit temporaries and return a name, instead of
appending to one buffer. This is the largest single change in the plan.

Unverified: the exact MP-SPDZ Matrix API names. MP-SPDZ is not on disk here, so
these must be confirmed against the `Compiler` module inside the image before
the translator is written. Doing that first avoids writing to a guessed API.

## Step 2. Move injection from bytecode to source

Files: `pipeline/injector.py`, `pipeline/gadgets/`.

Today the injector compiles the same source twice and mutates the tape of one
compiled program, splicing `addsi` / `mulsi` after a secret-writing anchor,
then compares `sync_signature` between honest and mutated tapes.

Changes, following `notes/circil-injection-plan.md`:

- Mutation moves to the CircIL AST, before translation.
- The pipeline becomes generate, inject on the AST, translate twice, compile
  twice, execute.
- `sync_signature` stays as the post-compile invariant check. It is the thing
  that refuses to run a mutation that reshaped inter-party message flow.
- The bytecode gadget helpers (`find_secret_writers`, `make_addsi`,
  `make_mulsi`, destination redirection) become unused for the matrix family.

Open decision: whether to delete the gadget path or keep it for the existing
field family. Recommendation is to keep it until the source-level path has
produced one campaign, then remove it rather than leaving two injectors.

## Step 3. Image rebuild and smoke run

`./containers/build.sh pipeline` bakes `pipeline/` and `python-circil/` into the
image, then `containers/run-campaign.sh` drives the campaign. Both are run by
hand, not by the assistant.

First smoke: mascot, n=2, honest circuit against a rearranged twin.

Pass condition: identical revealed output, no abort, and equal sync signatures.
Rearrangements are semantics-preserving, so any divergence here is a harness
defect, not a protocol finding. That is the point of running them first.

## Risks

1. `Matrix.dot` uses bulk Beaver triples, a different synchronisation class from
   scalar multiplication. If honest and rewritten tapes produce different sync
   signatures, the invariant check refuses to run and the approach needs
   rethinking. This is the main thing the smoke run exists to discover, and it
   is why it comes before writing injection rules.
2. Cost. A matmul is O(m*k*n) secret multiplications. Dimensions cap at 4, so a
   single call is at most 64, but circuits nest calls and the generator does not
   bound total multiplications.
3. The image copies `python-circil/` from the build context. The build must pick
   up the new clone, not `python-circil.old/`.
4. Input size. Baking matrix inputs as literals makes programs substantially
   larger than the scalar case, which affects compile time per run.

## Step 4. Unit 3, injection rules

Deferred until the above works.

Unit 3 introduces a term that the match did not bind, for example
`(matmul ?a ?b)` becoming `(matmul (add ?a ?r) ?b)`. These are deliberately
semantics-breaking and are the source-level equivalent of the existing bytecode
injections, bump (`a` to `a + r`) and sign flip (`a` to `-a`), which also get
ported here.

`?r` must be selected by searching the tree being rewritten for an existing node
of the required type. It is never synthesised. If no node of that type is in
scope, the rule does not fire, and that is a no-op rather than an error.

Two things are unresolved and will need deciding when unit 3 starts:

- CircIL's pattern DSL has `$r`, but it synthesises a random literal. That is
  the mechanism ruled out. Getting tree-sourced `?r` means either patching the
  pattern parser or building injection replacements in project-owned code
  instead of patterns.
- The scope machinery deleted in unit 2 (`SiteIndex`, the free-name and
  ancestor-interval tests) will be needed again in some form, because a node
  selected from elsewhere in the tree can reference identifiers that are not in
  scope at the splice point.
