# Fault-injection design (v0)

Consolidates the first exploration round. Revisit after reading "Rushing at SPDZ" and Arguzz §3 + Appendix B end-to-end.

## Methodology (from Arguzz, arXiv 2509.10819)

Arguzz fuzzes zkVM provers by **mutating instruction semantics at the bytecode-dispatch layer**, not at the cryptographic abstraction. The oracle is "verifier accepts mutated proof." Operators: replace opcode (ADD→SUB, →NOP), replace operand (constant, foreign register), skip instruction, corrupt branch condition, corrupt memory value, corrupt address. Only executed instructions are mutated. Prioritises hot paths.

**Port to MPC:** one corrupt party runs a mutated VM; honest parties run clean. Oracle = "protocol did not abort AND output ≠ honest-run output."

## Why the VM layer, not the protocol layer

MP-SPDZ's bytecode is **protocol-agnostic** — the Compiler emits one stream; `T::Protocol`, `T::MAC_Check`, `T::LivePrep` are wired in at link time per share type. Patch the dispatch once → every malicious protocol covered for free. Patching `ProtocolBase::exchange` / `MAC_Check_Base` works too but replicates logic per protocol family.

## Injection points

Primary: `Processor/Instruction.hpp:1530`, the opcode switch in `Program::execute_with_errors`. Wrap opcode lookup with a mutator.

Caveat: `ARITHMETIC_INSTRUCTIONS`, `CLEAR_GF2N_INSTRUCTIONS`, `REGINT_INSTRUCTIONS` (macros expanded inline at 1532–1543) bypass the default `Instruction::execute()`. Secondary shim: mutate at register access (`Procp.get_S()[reg]` in `Processor.hpp`) to cover arithmetic opcodes and memory-value faults.

## Fault operator catalog (ranked)

1. **Skip CHECK** (opcode 0xAF) — Rushing-at-SPDZ template.
2. **Skip TRUNC_PR** (0xA9) — the specific site Rushing-at-SPDZ attacked.
3. **Replace opcode** — ADDS↔SUBS, MULS→ADDS, etc. MAC check should catch.
4. **Corrupt γ_i** — leave share intact, mutate MAC. SPDZ-family only. Probes `(x_i, γ_i)` pairing across code paths.
5. **Operand foreign register** — substitute stale share.
6. **Corrupt opening message** at network layer — Rushing-style timing.
7. **Corrupt stored share** post-STMS.
8. **Operand constant 0 / max**.
9. **Branch condition corruption** (JMPNZ etc.) — lowest value; logic bugs, not core crypto.

## Synchronisation invariant

MP-SPDZ's network layer is async but **round counts and message volumes must match** across parties, or honest parties hang. Rule: mutate *values*, not *calls*. Safe-to-skip: CHECK, TRUNC_PR (local part), pure-local arithmetic. Unsafe-to-skip: MULS, OPEN, anything that triggers `protocol.exchange()` or `MC.exchange(P)`. To mutate a communicating opcode, call the method but corrupt its inputs/outputs.

## Propagation filter

Most mutations are no-ops (value computed but never opened). Build a **backward def-use slice** from every OPEN / CHECK / PRIVATEOUTPUT over the bytecode — only PCs in the slice are worth mutating. Dynamic taint-tracking is a more precise fallback. This is extra work Arguzz didn't need (they have one proof artifact).

## Oracle

Twin-run with pinned randomness (PRNG seed + pre-generated offline data reused across both runs):

- Baseline run: no mutation, record outputs and exceptions.
- Mutated run: one party's VM is patched, record outputs and exceptions.

Classification:
- `mac_fail` / `consistency_check_fail` in mutated run → protocol caught the deviation → **not a bug**.
- Mutated run succeeds, outputs differ → **soundness bug**.
- Segfault / assertion → liveness bug, triage separately.

Exception types in `Tools/Exceptions.h`. Abort call sites: `Protocols/MAC_Check.hpp:197`, `Protocols/SecureShuffle.hpp:318`, others.

## Party-role coverage (orthogonal concern)

The injector is symmetric; the harness iterates `(operator, corrupt_party_index)` per protocol. Symmetric families (SPDZ / MASCOT / SPDZ2k / MaliciousShamir): one party index suffices. Role-asymmetric families need per-role coverage:

- Rep3 / MaliciousRep3: `gen_player = 2, comp_player = 1` hardcoded (`Replicated.hpp:427`) — inject at 0, 1, 2.
- Astra: `gen_player = 0, comp_player = 1` (`Astra.hpp:445,480`) — inject at 0, 1.
- Trio: disjoint P0/P1/P2 roles in prep (`Trio.hpp:169,185,199`) — all 3.
- Dealer: last party is the dealer (`DealerInput.hpp:50`) — dealer + one non-dealer.
- Rep4: dynamic, but backup has extra check duty (`Rep4.hpp:118,131`) — all 4.
- Atlas: rotating king (`Atlas.h:29`) — one party if the run is long enough.

## Open questions (next session)

- Confirm MP-SPDZ actually supports pinned PRNG seeds and a reusable offline-data file. Agents asserted this; the `--seed` / triple-file flags were not verified against source.
- Inspect `Programs/Bytecode/*.sch`/`*.bc` format to confirm bytecode determinism across protocol choices.
- First concrete target: reproduce the Rushing-at-SPDZ truncation bug by "skip CHECK" applied around `TRUNC_PR`. If our harness catches it, the design works.

## Non-goals

- FHE / ZK internals.
- Covert protocols as a primary target (cowgear, chaigear) — same surface as malicious, just with probabilistic detection.
- Semi-honest protocols — already covered by BabelFuzz.
