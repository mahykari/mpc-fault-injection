# Rewrite-rule fuzzer: rare-type / rare-op surface

Prioritised by cost-to-try (cheapest first). Each tier: ops targeted, path,
why, and a hook rewrite pattern to start from. Full inventory is under
"Reference" at the bottom.

## Tier 1. Comparison on secret ints
- Ops: `<`, `<=`, `==`, `!=`, `>`, `>=` on `sint`
- Path: `types.sint.__lt__` → `comparison.LTZ` → `non_linear.eqz` / `PRandM`
- Why: no prior campaign has touched these; exercises bit-decomposition and
  `PRandM` for the first time
- Hook: `(<:bool ?a ?b) → (<:bool (+ ?a $r) ?b)`, mirror for `==` / `<=` /
  `!=`, and the symmetric right-operand variant

## Tier 2. Truncation
- Ops: `sint.__rshift__`, `mod2m`, `TruncPr`, `TruncMul`,
  `round(k, m, nearest, signed)`
- Path: `comparison.Trunc*`, `floatingpoint.TruncPr*`
- Why: this is where the historical Rushing-paper bug class lives;
  probabilistic truncation is the interesting one
- Hook: `(>>:?t ?a ?b) → (>>:?t (+ ?a $r) ?b)`; also mutate the shift amount
  independently

## Tier 3. Division / inverse
- Ops: `sint / sint`, `int_div`, `private_division(active=...)`
- Path: inverse triples; `floatingpoint.SDiv`, `SDiv_mono`
- Why: rare in stock programs; `private_division` has explicit `active`
  branching worth poking
- Hook: `(/:?t ?a ?b) → (/:?t (+ ?a $r) ?b)`

## Tier 4. Containers: matmul, sort, shuffle
- Ops: `Matrix.dot`, `direct_mul`, `Array.sort`, `secure_shuffle`,
  `secure_permute`, `inverse_permutation`
- Path: bulk-Beaver primitive; `Protocols/Shuffling.hpp` at the C++ layer;
  radix sort for `sint`/`sfix`, Batcher's odd-even mergesort for `sfloat`
- Why: a distinct sync class (bulk triples + shuffle-correctness) separate
  from scalar mult
- Hook: rewrite an element or permutation index;
  `(matmul ?A ?B) → (matmul (+ ?A $R) ?B)`

## Tier 5. Fixed / float / transcendentals
- Ops: `sfix.*`, `sfloat.*`, `mpc_math.{sin, cos, exp2, log2, sqrt, atan,
  InvertSqrt}`
- Path: rides on Tiers 1-3 plus `sfloat`'s own opcode stack and Aly-Smart
  polynomial evaluators
- Why: composes every earlier tier; good for depth once tiers 1-4 have
  been swept
- Hook: rewrite `sfix.v`; a deviating underlying int cascades through the
  whole pipeline

---

# Reference: full surface

Raw docstrings + line anchors live in the four Explore-agent runs from the
2026-07-19 session. Grep these names in the files below.

## Arithmetic scalars — Compiler/types.py
- Register-level: `_number`, `_int`, `_bit`, `_gf2n`, `_structure`,
  `_secret_structure`, `_vec`, `_register`, `_arithmetic_register`, `_clear`
- Clear: `cint`, `cgf2n`, `regint`, `localint`, `personal`, `longint`
- Secret: `_secret`, `sint`, `sintbit`, `sgf2n`, `_bitint`, `intbitint`,
  `sgf2nint`, `sgf2nuint`, `sgf2nuint32`, `sgf2nint32`, `sgf2nfloat`

## Fixed-point / float / quantized — Compiler/types.py
`cfix`, `_single`, `_fix`, `sfix`, `unreduced_sfix`, `squant`,
`_unreduced_squant`, `squant_params`, `sfloat`, `cfloat`

## Containers — Compiler/types.py
`_vectorizable`, `Array`, `SubMultiArray`, `MultiArray`, `Matrix`,
`VectorArray`, `_mem`, `MemValue`, `MemFloat`, `MemFix`

## Binary / GC — Compiler/GC/types.py
`bits`, `cbits`, `sbits`, `sbitvec`, `bit`, `sbit`, `cbit`, `bitsBlock`,
`dyn_sbits`, `DynamicArray`, `sbitint`, `sbitintvec`, `cbitfix`, `sbitfix`,
`sbitfixvec`, `cbitfloat`

## GC instructions with non-trivial add_usage — Compiler/GC/instructions.py
- Triples: `andrs`, `andrsvec`, `ands`
- Share conversion: `split`
- Randomness / I/O: `bitb`, `reveal`, `inputb`, `inputbvec`

## Rare-op modules

### Compiler/comparison.py
`LTZ`, `LtzRing`, `LtzRingRaw`, `Trunc`, `TruncRing`, `TruncZeros`,
`TruncLeakyInRing`, `TruncRoundNearest`, `Mod2m`, `Mod2mRing`, `Mod2mField`,
`MaskingBitsInRing`, `PRandM`, `PRandInt`, `BitLTC1`, `carry`, `CarryOut`,
`CarryOutRaw`, `CarryOutLE`, `BitLTL`, `PreMulC` family (with/without
inverses, vectorised), `KMulC`, `Mod2`

### Compiler/floatingpoint.py
`EQZ`, `PreORC`, `PreOpL`, `PreOpL2`, `PreOpN`, `PreOR`, `KORL`, `KORC`,
`KOR`, `KMul`, `Inv`, `BitAdd`, `BitDec`, `BitDecRing`, `BitDecField`,
`Pow2`, `Pow2_from_bits`, `B2U`, `Trunc`, `TruncInRing`, `SplitInRing`,
`TruncRoundNearestAdjustOverflow`, `Int2FL`, `FLRound`, `TruncPr`,
`TruncPrRing`, `TruncPrField`, `SDiv`, `SDiv_mono`, `BITLT`, `BitDecFull`

### Compiler/non_linear.py
`NonLinear`, `Masking`, `Prime`, `KnownPrime`, `Ring` (dispatch strategy)

### Compiler/sorting.py
`reveal_sort`, `radix_sort`, `radix_sort_from_matrix`, `dest_comp`

### Compiler/permutation.py
`odd_even_merge`, `odd_even_merge_sort`, `sort`, `configure_waksman`,
`waksman`, `iter_waksman`, `config_from_perm` (mostly dead; shuffle moved
into the VM)

### Compiler/mpc_math.py
`trunc`, `p_eval`, `sTrigSub`, `ssin`, `scos`, `sin`, `cos`, `tan`,
`exp2_fx`, `mux_exp`, `log2_fx`, `pow_fx`, `log_fx`, `abs_fx`, `floor_fx`,
`MSB`, `norm_simplified_SQ`, `sqrt_simplified_fx`, `norm_SQ`, `lin_app_SQ`,
`sqrt_fx`, `sqrt`, `atan`, `asin`, `acos`, `tanh`, `Sep`, `SqrtComp`,
`InvertSqrt`

## Composite modules

- `Compiler/oram.py`: `TrivialORAM`, `LinearORAM`, `TreeORAM`,
  `PackedORAMWithEmpty`, `RecursiveORAM`, `OptimalORAM` (+ debug variants)
- `Compiler/circuit_oram.py`: `CircuitORAM`, `RecursiveCircuitORAM`,
  `OptimalCircuitORAM`
- `Compiler/path_oram.py`: `PathORAM`, `RecursivePathORAM`
- `Compiler/sqrt_oram.py`: `SqrtOram`, `PositionMap`,
  `RecursivePositionMap`, `LinearPositionMap`
- `Compiler/path_oblivious_heap.py`: `PathObliviousHeap`,
  `UniquePathObliviousHeap`, `PathMinTree`, `CircuitMinTree`,
  `path_oblivious_sort`
- `Compiler/dijkstra.py`: `HeapORAM`, `HeapQ`, `dijkstra`
- `Compiler/decision_tree.py`: `TreeTrainer`, `TreeClassifier`, `Sort`,
  `VectMax`, `GroupSum`, `GroupPrefixSum`, `GroupMax`, `ModifiedGini`
- `Compiler/ml.py`: `Dense`, `Conv2d`/`FixConv2d`, `MaxPool`,
  `AveragePool2d`, `BatchNorm`, `LayerNorm`, `Relu`, `Gelu`, `Tanh`,
  `Square`, `Dropout`, `Argmax`, `Concat`, `Add`, `BertLayer`,
  `MultiHeadAttention`, `Optimizer`, `Adam`, `SGD`
- `Compiler/circuit.py`: `Circuit` (Bristol Fashion), `ieee_float`,
  `sha3_256`, `sha256`
- `Compiler/gs.py`: `Matchmaker` (Gale-Shapley matching)
