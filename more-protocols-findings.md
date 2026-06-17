# more-protocols — findings

Parked until containerization (`parallel-runs`) lands — the container entry point rewrites the launch path, the one surface this work overlaps.

## Decisions

- **Drop `semi`.** Semi-honest has no detection mechanism, so a deviation just deviates — nothing to soundness-test. Only target protocols with a malicious-security check to defeat.
- **Targets:** `spdz2k` and `malicious-shamir`.

| protocol | family | domain | threshold | "caught" stderr |
|---|---|---|---|---|
| `spdz2k` | dishonest-maj malicious, Z/2^k | `-R k` (no `-P`) | t < n | `"MacCheck Failure"` |
| `malicious-shamir` | honest-maj malicious | `-P p` + `-T t` | t < n/2 | `"inconsistent Shamir secret sharing"` |

Both throw `mac_fail` (Tools/Exceptions.h:95); shamir overrides the message (MaliciousShamirMC.hpp:59), so the oracle's hardcoded `"MacCheck Failure"` match misses it.

## Design

One `ProtocolSpec` table keyed by the protocol literal, carrying:

- `binary`
- `domain` — `Prime(p)` | `Ring(k)`; `Config.field_prime` moves into `Prime` (spdz2k has no prime)
- `threshold` — dishonest (t<n) | honest-majority (t<n/2)
- `catch_signatures` — stderr strings meaning "caught"

The `domain` feeds **both** compile and runtime argv:

- compile: flags go into `MpSpdzCompilerToolkit.compile`'s `custom_args` (today only `[program_id]`). Compiler option parser takes `-R`/`-P`/`-F` (compilerLib.py:157-193). Ring genuinely must change here — else spdz2k compiles for field and mismatches the ring binary.
- runtime: `-R k` vs `-P p` (+ `-T t` for shamir).

Put runtime argv on the spec (`runtime_args(...)`) so the container launcher consumes it — don't hardcode mascot's `-P/-N` into the entry point, or spdz2k/shamir become entry-point surgery later.

`malicious-shamir` honest-majority → corrupt-set sampling must respect t<n/2 (n=3 → |S|≤1).

## Files that change when resumed

`types.py`, `config.py`, `mpspdz.py`, `oracle.py`, `main.py`.
