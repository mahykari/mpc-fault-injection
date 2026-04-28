# mpc-fault-injection

Exploring fault injection for testing MPC protocol implementations.

## Context

[BabelFuzz](https://github.com/Rigorous-Software-Engineering/BabelFuzz) tests
MPC compilers for logic bugs using metamorphic and differential testing.
It found 27 bugs across MP-SPDZ, EMP, EzPC, and Silph —
but it only tests semi-honest execution (all parties follow the protocol).

This project explores the next step:
**fault injection to test malicious-security mechanisms**.
The idea is to simulate a corrupt party deviating from the protocol
and check whether the implementation correctly detects the deviation.

This is the MPC analogue of what
[ARGUZZ](https://github.com/Rigorous-Software-Engineering/arguzz)
does for zkVMs — inject faults into the prover and check if the verifier catches them.

## Key questions

1. **What is checked?**
   MAC checks, consistency checks, sacrificing, OT correlation checks.
   These are the mechanisms that distinguish malicious-secure protocols
   from semi-honest ones.

2. **Where do we inject?**
   Shares, MACs, Beaver triples, messages during reconstruction,
   protocol-level messages between parties.

3. **What are our oracles?**
   - Soundness: if a party deviates, the protocol should abort (or correct).
     If it produces a wrong output silently, that's a bug.
   - Completeness: if all parties are honest, the protocol should succeed.
     (Already tested by BabelFuzz.)
   - Fairness: if one party learns the output, all should.

4. **Which protocols?**
   - SPDZ/MASCOT (dishonest majority, MAC-based)
   - Malicious Shamir (honest majority, error-correction at reconstruction)
   - Others supported by MP-SPDZ

## Related work

- **BabelFuzz** (FSE 2026): Differential + metamorphic testing of MPC compilers.
- **ARGUZZ** (USENIX Security 2026): Fault injection for zkVMs.
- **Circuzz** (CCS 2025): Metamorphic testing of ZK pipelines.
- **Rushing at SPDZ** (ePrint 2025/789): Manual security analysis finding
  real attacks on MP-SPDZ and SCALE-MAMBA (missing MAC checks,
  thread race conditions). This is what we want to find *automatically*.

## Targets

| Framework | Language | Protocols | Parties | Open source |
|-----------|----------|-----------|---------|-------------|
| MP-SPDZ   | Python-like DSL | 30+ (semi-honest and malicious) | n ≥ 2 | Yes |
| EMP Toolkit | C++ | Semi-honest 2PC (garbled circuits) | 2 | Yes |
| EzPC | C-like DSL | 2PC (ABY-based) | 2 | Yes |
| Silph | C subset | 2PC (ABY-based) | 2 | Yes |
| ABY3 | C++ | 3PC | 3 | Yes |
| MOTION | C++ | Various | n ≥ 2 | Yes |
| CrypTen | Python/PyTorch | Secret sharing | n ≥ 2 | Yes |

MP-SPDZ is the primary target: most protocols, flexible party count,
and the only framework where malicious-secure protocols are readily available
across multiple paradigms (SPDZ, Shamir, BMR).

## Structure

```
notes/           # Reading notes, protocol analysis
exploration/     # Code for poking at MP-SPDZ internals
```
