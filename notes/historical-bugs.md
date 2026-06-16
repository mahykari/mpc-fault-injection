# Historical bugs in MP-SPDZ (and kin)

WHY: scope check for the fuzzer. Knowing what actually shipped broken
tells us which bugs we can **surface**, which we can only **seed** to
validate the fuzzer, and which are **out** of reach of a deterministic
twin-run. That three-way sort is the useful part.

When surfacing, the fuzzer never touches MP-SPDZ. It injects a deviation
(a wrong value on the corrupt parties) via a trick; the bug — a
missing/weak check — is already there. If the deviation rides through
that unchecked path → silent wrong output = bug surfaced. If the check is
correct, it catches the deviation and aborts. Surfacing means *driving a
deviation onto the path where a check is already missing* — not creating
or disabling a check (the seed track does that, on purpose, separately).

Spine = MP-SPDZ `CHANGELOG.md` `Fixed security bug:` lines, cross-linked
to the fix commits; CVEs + the FudanMPL fuzzing dump + Rushing at SPDZ
(2025/789) fill the memory-safety and concurrency corners. All entries
are already-public fixes; catalogued uniformly.

**To read a commit:** `github.com/data61/MP-SPDZ/commit/<sha>` or
`gh api repos/data61/MP-SPDZ/commits/<sha> --jq .commit.message`.
`(rel X.Y.Z)` is the CHANGELOG section it was announced in.

## How to read: surface / seed / out

Three buckets, not a capability ladder:

- **Surface** — the fuzzer catches the bug with a *trick*: change the
  **input program** or the **runtime parameters**, leave MP-SPDZ source
  untouched, twin-run, watch for deterministic divergence. This is the
  real fuzzing. The MP-SPDZ **types are tricks** here — an input program
  using `sfix` routes a deviation into the truncation path.
- **Seed** — we deliberately re-introduce a known historical bug into the
  source, then check the fuzzer surfaces its *kind*. Validation, not
  discovery. Matches the seeded-bug binary already in the repo.
- **Out** — not catchable by a deterministic soundness/completeness
  twin-run. Probabilistic bugs (a biased RNG) leave no clean divergence;
  privacy leaks need a different oracle than output-diff.

We fuzz **single-thread** input programs. The only way to put threads in
an MP-SPDZ program is loop-level parallelism (`@for_range_multithread`,
`@multithread` — data-parallel chunking over a range), not arbitrary
thread spawning. So the concurrency class has no input-program trick
today; it's seed-or-out.

---

## Class: skip-check (missing check)

The dominant class. A malicious-only verification step is simply absent
on some path; a corrupt party deviates and nothing aborts.

- **Missing MAC check in probabilistic truncation**, SPDZ/MASCOT.
  `trunc_pr` opened/used values without the MAC check the rest of the
  pipeline enforces — silent wrong output. The cleanest in-the-wild
  skip-check; Rushing at SPDZ flags this one. — commit `7051e5ae` (rel 0.4.0)
- **Missing MAC checks in multi-threaded programs**: per-thread tapes
  finished without forcing the outstanding MAC check. — `5e714b22` (rel 0.3.7)
- **Missing shuffling check in PS-mod-2^k and Brain**. — `7bc156e5` (rel 0.3.7)
- **Missing check in binary Rep4**. — `212165b8` (rel 0.2.3)
- **Insufficient checks + PRNG seeding in Rep4** (related, later). — `85307a1b`
- **Missing check in MASCOT bit generation + various binary**. — `82926150` (rel 0.1.5)
- **Insufficient OT correlation check in SPDZ2k**. — `dad23a63` (rel 0.1.4)
- **Inputs not checked during random-bit generation**: "some protocols
  with supposed malicious security wouldn't check players' inputs." — `40f136fc` (rel 0.1.0)
- **Insufficient hash check**. — `f3d01663`
- **Missing XOR in Matyas–Meyer–Oseas** (hash construction). — `9e30c5d6`
- **Insufficient sacrifice in Mama**: triple sacrifice too weak → bad
  triples survive. — CHANGELOG rel 0.3.3 (no isolated SHA surfaced)
- **SPDZ2k under-checking per §3.4 of updated 2018/482**. — CHANGELOG
  rel 0.3.1; paper: https://eprint.iacr.org/2018/482

**Bucket: surface + seed, split by sub-class.**
- **Truncation** (`7051e5ae`): *surface*. An input program using `sfix`
  lands a deviation in `trunc_pr`'s unchecked reveal → deterministic
  wrong output on a buggy build, no source change. Also the model *seed*:
  flip `check=False` on a fixed build to validate detection.
- **Binary-prep / conversion** (`7bc156e5`, `212165b8`, `82926150`):
  *surface* — input programs using `sbitvec`/`sgf2n` exercise the
  arith↔binary checks.
- **OT-correlation** (`dad23a63`), **multi-thread MAC** (`5e714b22`),
  **sacrifice** (Mama, rel 0.3.3), **PRNG-seed** (`85307a1b`): *seed* —
  the gap is in preprocessing / threading; no input-program or
  runtime-param trick reaches it.

## Class: wrong-check (incorrect / mis-ordered check)

Check is present but computes the wrong thing or runs at the wrong time.

- **Wrong MAC check in SPDZ2k input tuple generation**. — `38be996e` (rel 0.2.2)
- **MAC key not removed on failure**: failed check left the key
  usable; feeds the MAC-key-leakage Rushing exploits concurrently. — `96aac1e8` (rel 0.4.1)
- **Check earlier to prevent selective-failure**: ordering bug — a later
  check let a corrupt party learn a bit via abort/no-abort before the
  guard fired. — CHANGELOG rel 0.3.3
- **Base OT receiver can force repeated outputs** (credit: Mike
  Rosulek). — `b3a3a6ed`
- **Insufficient security in non-interactive ZK proofs** (credit:
  Sebastian Hasler). — `15284ea7`

**Bucket: seed.** The defect is in the check's own logic; no input
deviation makes a correct check wrong. Plant the historical version,
confirm the fuzzer catches the kind. (MAC-key-on-failure leans
concurrency/leakage — closer to out.)

## Class: race / concurrency

Multi-threaded interleavings around opening and MAC checking.

- **Race condition in MAC check**. — `7bf16a74`, earlier `b86f29b6` (rel 0.3.7)
- **MAC check broken under multithreading** — separate fix a few
  releases earlier. — CHANGELOG rel 0.3.3
- **MAC-key-leakage attack**, Rushing at SPDZ: a *concurrent* exploit
  of the above — needs threads racing the check to extract the key.
  Patched MP-SPDZ + FRESCO; SCALE-MAMBA analysed. — paper
  https://eprint.iacr.org/2025/789.pdf

**Bucket: seed / out.** Needs a thread interleaving; we fuzz single-thread
programs and MP-SPDZ only threads via loop-parallel chunks. The
*consequence* (a missing/late check) can be seeded deterministically; the
interleaving itself is out until there's a concurrency substrate.

## Class: randomness / bias

Insufficient or skewed randomness in preprocessing, keys, or bit gen.
Breaks security without any check being involved.

- **Bias in Rep3 secure shuffling**. — CHANGELOG rel 0.3.9
- **Skewed random bit generation**. — `eaf3d00e` (rel 0.2.5)
- **Insufficient LowGear secret-key randomness**. — CHANGELOG rel 0.2.5
- **Insufficient randomness in SemiBin random-bit gen**. — CHANGELOG rel 0.2.0
- **Insufficient randomization of FKOS15 inputs**. — `99c5efc1` (rel 0.2.0)
- **All-zero secret keys in HE**. — `93ac1e9e` (rel 0.2.3)
- **Insufficient randomizing in GF(p)**. — `1f5b7e88`

**Bucket: out.** Probabilistic — a biased draw leaves no deterministic
divergence for twin-run. (A *missing check* downstream of bad randomness
is a skip-check, sorted there; the bias itself is what's out.)

## Class: privacy leak (under-masking)

Output or intermediate reveals more than it should. Soundness fine;
privacy isn't.

- **Missing randomization before revealing to client**. — CHANGELOG rel 0.3.9
- **Insufficient drowning in pairwise protocols**: statistical mask too
  small → leaks share info. — CHANGELOG rel 0.3.7
- **Revealing too much when opening linear combinations of private
  inputs**, MASCOT/SPDZ2k with >2 parties. — CHANGELOG rel 0.0.9

**Bucket: out.** Wrong oracle — output-diff won't see a leak that doesn't
corrupt the output. Needs a leakage oracle regardless of trick.

## Class: arithmetic / accounting

Wrong counts, reused material, off-by-something in bookkeeping.

- **Improper accounting for random elements**. — `9d578a37` (rel 0.3.6)
- **CowGear reused triples**: reuse → exploitable correlation. — `5f0a7ad8` (rel 0.1.2)
- **Binary computation bug in SPDZ(2k)**. — `bd3366a0` (rel 0.2.0)

**Bucket: surface — our home.** A perturbed share rides the open/MAC-check
pipeline; on a buggy build a weak accounting check lets it slip →
deterministic divergence. We don't reproduce the accounting bug; we ride
a deviation through whatever weak check it left. The reuse class is also
*seedable* for sharper validation.

## Class: HE-specific

Homomorphic-encryption offline phase. Outside our world.

- **HE parameter generation**. — `a858e5b4` (rel 0.3.2)
- **Temi matrix multiplication**. — `db676351` (rel 0.3.2)
- **Ciphertext-correctness proof missing in input tuple gen**. — CHANGELOG rel 0.1.5
- **Insufficient "blaming" in CowGear/ChaiGear**: covert-security
  parameter set too low. — CHANGELOG rel 0.2.3

**Bucket: seed.** Source-level only — the defect is in the FHE offline
phase, no input-program trick reaches it. Low value.

## Class: memory-safety / DoS (not soundness)

Remotely-triggered crashes from malformed network messages. For
completeness — availability bugs, not malicious-MPC soundness.

- **Remotely caused buffer overflows** (issue #1382). — `6ce15d4e` (rel 0.3.9):
  - CVE-2024-33783 — SEGV in `SilentMultiPprfReceiver::expand`,
    `Tools/SilentPprf.cpp`.
  - Stack overflow in `OTExtensionWithMatrix::extend`,
    `OT/OTExtensionWithMatrix.cpp`.
  - Stack overflow in `octetStream::get_bytes`, `Tools/octetStream.cpp`.
  - Reported by FudanMPL's network-input fuzzer:
    https://github.com/FudanMPL/Vulnerabilities-in-MPC-Framework
    (`MP-SPDZ/` subdir, one PoC dir per crash). Orthogonal to our IR
    injector.

**Bucket: out.** Crafted network bytes, not an input-program deviation;
a crash is "inconclusive" in twin-run. Network fuzzer's job (ala
FudanMPL's), not ours.

---

## Takeaway for scope

**Surface (real fuzzing, now).** Arithmetic/accounting and the truncation
skip-check are catchable today with input-program tricks on a buggy
build — no source change. `sfix` is the highest-signal type: it lands
deviations in the truncation path. Widen across `sbitvec` (conversion
checks) and batch-open `Array`/`Matrix` (accounting path) next. The open
question is breadth — which input programs, types, and runtime params to
sample.

**Seed (validation, in parallel).** Re-introduce known historical bugs
and confirm the fuzzer surfaces their kind. The truncation `check=False`
flip is the cheapest, highest-fidelity seed; matches the seeded-bug
binary already in the repo. Wrong-check, OT-correlation, sacrifice, and
HE all sit here — the bugs we can't surface but can still validate
against.

**Out (for now).** Probabilistic bugs (biased RNG) and privacy leaks —
wrong oracle. Concurrency — single-thread fuzzing plus loop-only
threading means there's no interleaving to ride. Revisit if the oracle
or a concurrency substrate gets built.
