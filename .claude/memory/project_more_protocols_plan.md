---
name: project_more_protocols_plan
description: more-protocols — ProtocolSpec table implemented in worktree; pending patched-binary build + spdz2k/shamir smoke test
metadata: 
  node_type: memory
  type: project
  originSessionId: 4ffe85be-71f6-488d-a797-ae04643879df
---

ProtocolSpec adds spdz2k + malicious-shamir to the MASCOT-only fuzzer. **Implemented in the `more-protocols` worktree on 2026-06-29** (after merging master to pick up containerization). mypy green, mascot regression 3/3 caught.

What landed:
- `pipeline/protocols.py` (new) — `Prime(prime)` / `Ring(k)` domains (each with `compile_args` + `runtime_args`), `ProtocolSpec(domain, honest_majority, catch_signatures)` with `max_corrupt(n)` + `threshold_args(n)`, and `PROTOCOL_SPECS` table. `PRIME_MERSENNE_M127` lives here now.
- `Config` — `field_prime` removed (it's in `Prime`); `spec` @property; `__post_init__` corrupt-set guard (1 ≤ |S| ≤ t; honest-maj t=(n-1)//2, dishonest t=n-1). Views: NeedsPartyBinary/NeedsCompilerToolkit gain `spec`, new NeedsOracle.
- `mpspdz.py` — `compile` prepends `domain.compile_args` (`-R k` for ring); `_spawn` argv = common + `domain.runtime_args` (`-P prime` | `-R k`) + `threshold_args` (`-T t` for shamir), dropped hardcoded `-P field_prime`.
- `oracle.py` — `judge(run, config)`; matches any `spec.catch_signatures` (shamir's "inconsistent Shamir secret sharing" now → caught).
- build flow — `containers/{Containerfile,build.sh}` take a `PARTY_BINARIES` build-arg; `patched`/`pipeline` build+extract all three, `seeded-bug` stays mascot-only.

Key correction to the old parked plan: containerization is **instance-level** (launch.py spawns containers; party launch stays in `mpspdz.py:_spawn`), so runtime argv was never in the container entry point — it's in `_spawn`. No entry-point surgery needed.

Blocker that's now a build step: the 0001 `check_program` no-op patch is **templated** (`Machine<sint,sgf2n>`) → applies to any binary built from the patched tree. Stock spdz2k/shamir abort the twin-run at startup, so they need patched builds. Patched dir had only mascot.

**Pending (user's button):** run `./containers/build.sh patched` to build+extract all three patched binaries, then smoke-test:
- spdz2k: `CONFIG='{"protocol":"spdz2k","n_parties":3,"malicious_parties":[0,1],"seeds":[0,1,2]}'`
- malicious-shamir (t=1): `CONFIG='{"protocol":"malicious-shamir","n_parties":3,"malicious_parties":[0],"seeds":[0,1,2]}'`

Protocol selection is per-run via the existing CONFIG override — no campaign code. Generator emits only +/-/* over sint, so programs are ring-safe for spdz2k.

See [[project_shared_mutated_bytecode]], [[feedback_code_structure]], [[project_check_program_blocker]], [[project_containerization_rationale]].
