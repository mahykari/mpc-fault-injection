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

## Status

The harness is at the **plumbing milestone**: a hand-written program is
compiled to MP-SPDZ IR, an `Injector` mutates one IR copy (LDSI immediate
swap), both copies are written to disk, and `mascot-party.x × 2` is launched
twice (honest twin, mutated twin) from Python. The mutated twin currently
trips MASCOT's MAC check at OPEN — the real malicious-security mechanism.

What's still stubbed: real `Generator` + `Translator` (driven by
`python-circil`), gadget-based `Injector` (only LDSI swap today), real
`Oracle` (BLUEPRINT decision table), real `Reporter` (writing
`runs/<id>/report.json`).

## Repository layout

```
BLUEPRINT.md          — design source of truth (architecture, threat model, components)
CLAUDE.md             — instructions for Claude Code
main.py               — pipeline entrypoint (`uv run python main.py`)
pipeline/             — typed pipeline components (Generator … Reporter), Config, MP-SPDZ adapters
patches/mpspdz/       — C++ source patches applied to MP-SPDZ at build time
docker/               — Dockerfile + build.sh for the patched mascot-party.x
notes/                — protocol analysis, MP-SPDZ architecture map, patching notes
exploration/          — scratch scripts for poking at MP-SPDZ
MP-SPDZ/              — gitignored: pre-built v0.4.2 distribution + Compiler/ Python module
python-circil/        — gitignored: input-program generator (clone separately)
runs/                 — gitignored: per-run artifacts
```

`BLUEPRINT.md` is the source of truth for design decisions. Read it before
making structural changes.

## Running it

Prerequisites:
- [uv](https://github.com/astral-sh/uv) for Python.
- A working MP-SPDZ v0.4.2 distribution at `./MP-SPDZ/`. The repo is
  gitignored; download the pre-built tarball:
  ```sh
  curl -L -o /tmp/mp-spdz.tar.xz \
    https://github.com/data61/MP-SPDZ/releases/download/v0.4.2/mp-spdz-0.4.2.tar.xz
  tar -xJf /tmp/mp-spdz.tar.xz && mv mp-spdz-0.4.2 MP-SPDZ
  ```
- Docker, only if you want to (re)build the patched binary used by the
  pipeline (see below). The first build takes ~7–10 min; rebuilds are
  fast thanks to layer caching.

Run the pipeline:

```sh
uv run python main.py
```

Type-check:

```sh
uv run mypy
```

`uv run python main.py` and `uv run mypy` must both succeed at all times —
the pipeline-runs-end-to-end and `mypy --strict` invariants are
load-bearing (BLUEPRINT.md § "Development invariants").

### Patched mascot-party.x

`Config.use_patched_binary` (set in `main.py`) tells the pipeline which
party binary to launch:

| Flag | Binary | What it does |
|---|---|---|
| `False` | `MP-SPDZ/bin/Linux-amd64/mascot-party.x` | Stock v0.4.2; trips on the slightest cross-party bytecode divergence (catches every twin-run before any actual protocol step). |
| `True`  | `MP-SPDZ/bin/Linux-amd64-patched/mascot-party.x` | Built from source via `docker/build.sh` with `patches/mpspdz/0001-noop-check-program.patch` applied; lets twin-runs reach the actual protocol layers. |

To produce the patched binary:

```sh
docker/build.sh
```

The script builds inside `ubuntu:22.04` (host Boost is too new for libOTe)
and extracts `mascot-party.x` into `MP-SPDZ/bin/Linux-amd64-patched/`.
Re-run after editing anything in `patches/mpspdz/`. See
`notes/mpspdz-patching.md` for the patching strategy and
`patches/mpspdz/README.md` for the patch table.
