# Patching MP-SPDZ

WHY: BLUEPRINT's twin-run design (corrupt party loads different
bytecode) is blocked at startup by a fingerprint check that MP-SPDZ
runs before any computation. To do real IR-level fault injection we
need to disable that check (and likely more, as we hit them).

## What we've found

### `check_program` is the immediate blocker

`Processor/Machine.hpp:769` — `Machine::check_program()` hashes each
tape's raw `.bc` bytes, combines into a per-Program hash, broadcasts
via `Bundle::compare`, and aborts on disagreement. Called from
`Machine::prepare()` at line 162, before any computation.

`Processor/Program.cpp:75-86` — the hash is computed over the entire
raw `.bc` file (SHA-style, chunk reads).

Runs in **every protocol**, including semi-honest. It's a baseline
runtime-integrity check, not a malicious-security mechanism. Removing
it is not "removing protection we wanted to test" — it's removing a
plumbing layer below malicious security.

Verified: our LDSI-immediate mutation (1 → 42) survives finalize,
changes the bytecode hash, and is caught here:
`Fatal error: program differs between parties`.

### Bypass options ruled out

- **LD_PRELOAD on `check_program`** — `mascot-party.x` is stripped
  and statically linked (only libc/libdl/libm/libpthread dynamic).
  No internal symbols exported. Won't work.
- **Host source build** — fails on Boost 1.90 / libOTe ASIO
  incompatibility (Ubuntu 26.04). Per CLAUDE.md.

### Bypass we're going with

Container build (Ubuntu 22.04 + Boost 1.74) of a patched
`mascot-party.x` where `check_program` is a no-op. Both parties run
the patched binary (one-sided skip would deadlock — `check_program`
does a synchronous broadcast).

## What kinds of patches we'll accumulate

| Kind | Lives in | When |
|---|---|---|
| **Adapter wrappers** (Python) | `pipeline/mpspdz.py` | Already in place: singleton reset, module-globals rebind, chdir, pre-mkdir |
| **C++ source patches** | `patches/mpspdz/NNNN-*.patch` | Now: `check_program`. Soon: MAC checks, sacrifice, OPEN consistency — as experiments demand |
| **Schedule / preprocessing patches** | TBD | When we want to fault the offline phase or `.sch` |
| **Runtime injection** (ptrace / mitm) | TBD | For race conditions, network-level faults (e.g. "Rushing at SPDZ" thread races) |
| **Binary patches** | last resort | If a source patch becomes unwieldy |

Only C++ source patches require the container. Adapter wrappers stay
in our code where we can iterate freely.

## Plan: container-built patched binary

### Directory shape

```
patches/mpspdz/
  README.md                       # numbered table: # | target | why
  0001-noop-check-program.patch   # vs Processor/Machine.hpp:769–785
docker/
  Dockerfile.mpspdz               # ubuntu:22.04 + deps + source + patches + make
  build.sh                        # docker build + extract binary
MP-SPDZ/bin/Linux-amd64-patched/  # gitignored output
  mascot-party.x
```

### Build environment

- `ubuntu:22.04` base.
- Apt: `build-essential libboost-thread-dev libboost-filesystem-dev
  libsodium-dev libgmp-dev libssl-dev libntl-dev automake yasm m4 python3`.
- Download MP-SPDZ source tarball at `v0.4.2` (matches our stock binary version).
- `patch -p1 < patches/mpspdz/*.patch` in numbered order.
- `make -j mascot-party.x`.
- Statically link Boost etc. so the runtime host only needs libc.

### Build vs run cost

- Container is **for building only**. Pipeline runs invoke the binary
  natively via `subprocess.Popen` — no Docker in the hot path.
- First build: ~5–10 min. Patch-only rebuild: ≲1 min (Docker layer cache).
- Pipeline run cost: unchanged (~100–200 ms for the toy 8-instruction
  twin pair).

### Harness wiring

`Config.use_patched_binary: bool` (default True once build exists).
`Config.party_binary_path` chooses `Linux-amd64-patched/` vs `Linux-amd64/`
based on the flag. Derivation stays as a single `@property`.

## Sequencing for next session

1. **Commit the IR-mutation integration** if not already done.
2. **Get a clean v0.4.2 source tree** to diff against (re-extract the
   tarball to a temp dir).
3. **Write `0001-noop-check-program.patch`** — body of `check_program()`
   becomes `return;`. Keep patch narrow (don't bundle).
4. **Write `Dockerfile.mpspdz` and `docker/build.sh`.** First build to completion.
5. **Smoke test the patched binary** — run with the *same* honest bytecode
   on both parties; should still print `result: 3`. Patch shouldn't break
   the happy path.
6. **Add `use_patched_binary` to `Config`**, re-run pipeline.
7. **Observe what catches the mutation next.** Probably the MAC layer
   at `.reveal()`/OPEN (`Protocols/MAC_Check.hpp:197`, per BLUEPRINT).
   That's the actual malicious-security mechanism we want to probe.
8. Whatever happens: record it. If MASCOT catches, log the verdict and
   move on. If MASCOT misses (silent wrong output), that's a soundness
   bug candidate — investigate.

## Risks

- **Patch fails to apply** on minor MP-SPDZ source updates → narrow patches,
  easy to hand-fix.
- **Patched binary trips a different check** → that's the point. Add
  `0002-...` for the next layer if needed for the research thesis.
- **Build deps drift** → pin `ubuntu:22.04` and MP-SPDZ tarball at `v0.4.2`.
  Don't `apt-get upgrade` in the Dockerfile.
- **Disabling too much** → if patches reach into MAC generation or
  consistency checks themselves, the protocol is effectively semi-honest
  and the harness becomes meaningless. Discipline: only disable plumbing
  (things that exist in semi-honest too), never the malicious-security
  mechanisms themselves.

## Findings worth remembering (not just bugs to fix)

- **`Program.finalize` mutates module globals.** Compile-twice requires
  rebinding `Program.prog`, `instructions.program`, `instructions_base.program`,
  `types.program`, `comparison.program` before each finalize, otherwise
  optimization output routes to the wrong tape. Documented inline in
  `pipeline/mpspdz.py:_bind_module_globals`. List verified complete by
  `grep` across `Compiler/` — no other module-level `program` references.
- **MP-SPDZ Compiler is `Compiler.singleton`-enforced one-per-process.**
  We reset before each compile. Necessary for compile-twice (which we
  do for the honest/mutated pair).
- **Compile output is CWD-bound.** `program.programs_dir = "Programs"`
  is a relative path; chdir into the output dir before finalize.
- **`Compiler.program.Program` resists deepcopy.** Instruction objects
  have read-only descriptors (e.g. `arg_format`). That's why the Injector
  recompiles from source instead of deep-copying.
