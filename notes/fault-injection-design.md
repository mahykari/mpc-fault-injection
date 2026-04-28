# Fault-injection design (v0)

Consolidates the first two exploration rounds. Methodology is an Arguzz port; this note keeps the divergences explicit.

## Methodology (from Arguzz, arXiv 2509.10819)

Arguzz fuzzes zkVM provers by **mutating instruction semantics at the bytecode-dispatch layer**, not at the cryptographic abstraction. The oracle is "verifier accepts mutated proof." Operators: replace opcode (ADD→SUB, →NOP), replace operand (constant, foreign register), skip instruction, corrupt branch condition, corrupt memory value, corrupt address. Only executed instructions are mutated. Prioritises hot paths.

**Port to MPC:** one corrupt party runs a mutated VM; honest parties run clean. Oracle = "protocol did not abort AND output ≠ honest-run output."

## Threat model (clean statement)

A corrupt party in malicious MPC can only do one thing observable to honest parties: **change the bytes they put on the wire** (or fail to send them). Internal computation, randomness, register state — none of it matters to honest parties' view; they don't see it.

Wire-level menu:
- Send wrong bytes at a network round (corrupt share / MAC contribution / commitment / OT response).
- Send no bytes (refuse to participate → honest parties detect timeout, abort).
- Send late, after observing honest sends (rushing — defeated by commit-then-reveal where present).
- Send different bytes to different recipients (defeated by `Check_Broadcast` where present).
- Provide an adversarial input via INPUT.

That is the entire surface. Bytecode-dispatch injection is a **convenient proxy** for wire-level mutation: corrupting the share register before OPEN's exchange phase produces the same network effect as corrupting the wire bytes mid-round, with structured access to "this is the share for value v at PC p."

## Two experiments, kept separate

The harness mixes two distinct experiments. Confusing them was the source of half this design's earlier muddle.

**(E1) Attack simulation — the bug-finder.** Mutate the corrupt party's wire-level outputs (operand corruption at OPEN-time, MAC contribution corruption, message suppression). Run baseline + mutated, twin-run output diff. Silent divergence = honest parties accepted a real attack = real coverage gap in MP-SPDZ.

**(E2) Coverage-gap synthesis — the harness self-test.** Skip a CHECK opcode locally on the corrupt party (or any other purely-local instruction), creating a synthetic implementation bug. Run an attack against it. If the harness *catches* the synthetic bug (twin-run flags it), the harness works on this bug class. If not, the harness has a blind spot. **E2 is not a model of attacker behavior** — a corrupt party can't unilaterally suppress a multi-party check; honest parties still run it and detect the missing contribution as a timeout. E2 is "what if MP-SPDZ accidentally lacked a check here?" testing, not "what can Carol do?" testing.

Different oracles, different yields, different roles. Run them as separate harness modes.

## Why the VM layer, not the protocol layer

MP-SPDZ's bytecode is **protocol-agnostic** — the Compiler emits one stream; `T::Protocol`, `T::MAC_Check`, `T::LivePrep` are wired in at link time per share type. Patch the dispatch once → every malicious protocol covered for free. Patching `ProtocolBase::exchange` / `MAC_Check_Base` works too but replicates logic per protocol family.

## Injection points

Primary: `Processor/Instruction.hpp:1530`, the opcode switch in `Program::execute_with_errors`. Wrap opcode lookup with a mutator.

Caveat: `ARITHMETIC_INSTRUCTIONS`, `CLEAR_GF2N_INSTRUCTIONS`, `REGINT_INSTRUCTIONS` (macros expanded inline at 1532–1543) bypass the default `Instruction::execute()`. Secondary shim: mutate at register access (`Procp.get_S()[reg]` in `Processor.hpp`) to cover arithmetic opcodes and memory-value faults.

## Fault operator catalog (two axes)

The operator space splits along two orthogonal dimensions. Per-instruction operators mirror Arguzz; sequencing operators are MPC-specific because checks are deferred and batched (zkVM constraints are universal-per-transition; MPC checks are selective-per-batch).

### Axis A — instruction semantics (Arguzz import)

Per-PC mutations. Each is expressible as a wire-level deviation by the corrupt party.

1. **Corrupt operand at OPEN** — wire-level: send wrong share contribution. Highest-priority operator; this is the canonical attack.
2. **Corrupt γ_i** — leave share intact, mutate MAC contribution. SPDZ-family only. Probes `(x_i, γ_i)` pairing across code paths.
3. **Operand foreign register** — substitute stale share before OPEN.
4. **Operand constant 0 / max** — boundary mutation.
5. **Replace opcode** — ADDS↔SUBS, MULS→ADDS, etc. Tests whether downstream checks notice the substitution.
6. **Corrupt stored share post-STMS** — write through state to a value that gets opened later.

### Axis B — sequencing (MPC-specific)

Inter-PC mutations on **local opcodes only** (no wire effect of their own). These belong to E2 (coverage-gap synthesis), not to attacker simulation — except where they correspond to a missing-send (suppress contribution to a multi-party check).

7. **Skip a check** — drop CHECK, drop a sacrifice trigger, drop a MAC-accumulator push. Synthesises "what if this check were missing." Self-test only.
8. **Defer a check past consumption** — move CHECK after a downstream OPEN that depends on its accumulator. Tests whether other downstream protections still catch it.
9. **Reorder** — swap two non-communicating opcodes (e.g., CHECK with a downstream local arithmetic op).
10. **Window** — insert local arithmetic between an OPEN and the CHECK that covers it; tests whether un-checked values propagate into output before the abort can fire.
11. **Cross-tape racing** — perturb thread interleaving to force orderings that violate accumulator/barrier invariants. The Rushing-at-SPDZ thread-race bugs live here.
12. **Skip a multi-party-check contribution** — the corrupt party fails to broadcast σ at CHECK time. Wire-level: missing send. Honest parties should abort; if they don't, it's a real bug. (This one IS attacker simulation, not synthesis — the wire effect is real.)
13. **Branch flip on clear-register conditions** — JMPNZ/JMPI on a public value. Sync-safe (every party computes the same condition); the flip is local. Lowest priority.

### Excluded / Tier-2 (separate harness)

Operators that break the synchronisation invariant (skip MULS / OPEN / RUN_TAPE on the corrupt party): honest parties hang. These exit the soundness oracle and need a fairness/availability oracle — different experiment, separate plumbing. Subclass: skip-one-sync-fast-forward-to-next still deadlocks on the finite-syncs argument; belongs in Tier-2.

## Synchronisation invariant

MP-SPDZ's network layer is async but **round counts and message volumes must match** across parties, or honest parties hang. The cut that matters is **sync-preserving vs sync-breaking**, not values vs control flow.

**Sync-preserving (Tier 1, primary).** Anything that doesn't change the network trace seen by honest parties.
- Value mutations on any opcode (axis A 1–6).
- Control-flow mutations on local-only opcodes (axis B 7–11, 13). The Rushing-at-SPDZ truncation bug is exactly a control-flow skip in this set — "values not calls" was the wrong shorthand.

**Sync-breaking (Tier 2, separate harness).** Skip / duplicate any opcode that calls `Player::send` / `exchange` / `Check_Broadcast`. Different oracle: "did the protocol's identifiable-abort guarantee fire, or did honest parties hang silently?"

**Whitelist is a claim, not a fact.** Some "local" opcodes flush buffered network state (e.g., `MAC_Check::Check(Player)` does broadcast). Derive the local-opcode list by grepping each candidate handler in `Instruction.hpp` for `P.send` / `P.exchange` / `P.Check_Broadcast` / Player calls. One-time audit before writing the injector.

## Propagation filter

Most mutations are no-ops (value computed but never opened). Build a **backward def-use slice** from every OPEN / CHECK / PRIVATEOUTPUT over the bytecode — only PCs in the slice are worth mutating. For axis-B operators, the interesting object is a *pair* (PC_open, PC_check) or a *triple* (PC_open, PC_consume, PC_check) — the slice should also identify check-coverage relationships, not just data flow. Dynamic taint-tracking is a more precise fallback.

## Oracle

Twin-run with pinned randomness (PRNG seed + pre-generated offline data reused across both runs):

- Baseline run: no mutation, record outputs and exceptions.
- Mutated run: one party's VM is patched, record outputs and exceptions.

Classification:
- `mac_fail` / `consistency_check_fail` in mutated run → protocol caught the deviation → **not a bug**.
- Mutated run succeeds, outputs differ → **soundness bug** (E1) or **coverage gap** (E2 on a check that turns out to actually be redundant — interesting but rare).
- Mutated run hangs / times out → Tier-2 territory; soundness oracle says "no signal."
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

## Arguzz parallel — same class, three divergences

|                          | Arguzz (zkVM)                               | This project (malicious MPC)                    |
|--------------------------|---------------------------------------------|-------------------------------------------------|
| Cheater                  | Prover                                      | Corrupt party                                   |
| What they corrupt        | The execution trace they claim              | Bytes they send on the wire                     |
| Verifier mechanism       | Constraints over the trace                  | MAC check / RS reconstruction / sacrificing     |
| Bug                      | Constraints accept a wrong trace            | Honest parties accept output without abort      |
| Why bugs exist           | Constraint wrong / weak                     | Check missing / weak / has coverage gap         |

Three divergences:
- **Coverage shape.** zkVM constraints are universal (every transition). MPC checks are selective (per opening). Bug distribution skews toward *missing* (not *weak*) on our side. Rushing-at-SPDZ examples are missing-class.
- **Cheater's freedom.** Arguzz prover lies about any transition. Our corrupt party only lies about wire bytes. Strictly less freedom; smaller search space.
- **Sequencing dimension.** zkVM bugs are mostly per-instruction. MPC bugs are often *across* instructions (which check covers which open, in which batch). Axis B exists because of this.

Yield expectation: Arguzz-class. Handful of real bugs across the malicious-protocol surface. Pitch is "systematic differential fuzzer for malicious MPC implementations finds Rushing-at-SPDZ-class bugs across all 30+ malicious protocols MP-SPDZ ships." Not "we'll find new attacks on SPDZ."

## First concrete target

Reproduce the Rushing-at-SPDZ truncation bug:
1. **E2 self-test path:** in MP-SPDZ's TRUNC_PR, artificially excise the relevant check. Run a corrupt-share E1 mutation against the now-broken trace. Twin-run should flag silent divergence. If yes, harness works.
2. **E1 real-bug path:** without excision, sweep corrupt-share mutations across every OPEN in the test corpus. The TRUNC_PR opening should produce silent divergence on the affected MP-SPDZ versions; should be caught on patched versions. Confirms the harness rediscovers the real bug.

## Open questions (next session)

- Confirm MP-SPDZ actually supports pinned PRNG seeds and a reusable offline-data file.
- Inspect `Programs/Bytecode/*.sch`/`*.bc` format to confirm bytecode determinism across protocol choices.
- Audit which opcodes are truly local (no Player calls) vs. hidden-network — the axis-B whitelist depends on it.
- Decide whether the propagation-filter slice computation can reuse Compiler-emitted dependency information or needs to be rebuilt from bytecode.

## Non-goals

- FHE / ZK internals.
- Covert protocols as a primary target (cowgear, chaigear) — same surface as malicious, just with probabilistic detection.
- Semi-honest protocols — already covered by BabelFuzz (see `babelfuzz.md`).
- Multi-party collusion. Single-corrupt-party only; multi-corrupt-party is a strictly bigger search problem and a separate experiment.
- Privacy bugs. Our oracle is output divergence; bugs where a corrupt party *learns* something extra without affecting output are invisible to it.
