# BabelFuzz

Watzinger, Wüstholz, Garg, Christakis. *Cost-Effective Testing of MPC Compilers.* PACMSE Vol. 3, FSE-2026, Article FSE199. https://mariachris.github.io/Pubs/FSE-2026-MPC.pdf. Tool: https://github.com/Rigorous-Software-Engineering/BabelFuzz.

## What it does

Differential / metamorphic fuzzing of **MPC compilers** (not protocols). Generates programs in an expressive IR, translates them to multiple MPC DSLs (MP-SPDZ, EMP Toolkit, EzPC, Silph) **and** to plain Python. Runs each translation, compares outputs.

- **DT mode:** the Python translation is the oracle. Any divergence between an MPC compiler's output and the Python output is a logic bug in the MPC compiler.
- **MT mode:** apply semantics-preserving transformations to the IR; outputs of original and transformed programs should match. Catches features not modellable in the Python oracle.

## Threat model

**Semi-honest only.** From §5.2 (verbatim): *"we choose comparatively fast (i.e., semi-honest) protocols for the actual execution of MP-SPDZ programs."* Every run is all-honest. No party deviates.

## Bugs found

27 unique logic bugs across the four compilers (15 fixed). All are compiler/optimizer bugs: optimizer dropping write-after-write dependencies, sfix/cfix shallow copies, loop unrolling skipping iterations, fixed-point NaN, bit-shift/division of negatives, etc. **Zero touch malicious-security code paths** — those code paths weren't exercised because no run ran a malicious protocol.

## The gap our project fills

BabelFuzz tests the **Compiler box** of the architecture map under all-honest execution. We test the **Protocol box** under one-party deviation.

| Axis           | BabelFuzz                            | This project                                              |
|----------------|--------------------------------------|-----------------------------------------------------------|
| SUT layer      | Compiler (Python → bytecode)         | Protocol layer at the EXEC↔PROTO seam                     |
| Threat model   | All-honest                           | One Byzantine party                                       |
| Mutation       | Source program / IR                  | Bytecode dispatch on the corrupt party                    |
| Oracle         | MPC output vs. Python output         | Twin-run output diff under pinned randomness              |
| Bug class      | Optimizer / type / shallow-copy bugs | Missing / weakened malicious-security checks              |
| What signals   | Numerical divergence                 | Silent divergence without `mac_fail` / abort              |

The two are orthogonal and should be cited that way. BabelFuzz strengthens our positioning: there's now a published completeness fuzzer for MPC, and it explicitly punts on the malicious-security side. Future-work in BabelFuzz mentions only "additional language features and richer translations" — nothing about malicious security.

## Composability

BabelFuzz's seed corpus is exactly the program corpus we'd want to fault-inject into — diverse opcode coverage, well-defined semantics. "Use BabelFuzz seeds, run them under malicious protocols with one party's dispatcher mutated" is a defensible plan if upstream cooperation is feasible.
