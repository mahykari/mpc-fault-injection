# Fuzzing design

WHY: pin down the two fuzzing ideas for this project. The
softball is designed end-to-end; the football is scoped but
mostly TBD. BabelFuzz lives at the bottom as related work.

## Fault injection for MPC protocols: two complementary approaches

The goal is to automatically find bugs in malicious-secure MPC
protocol implementations — the same class of bugs that
"Rushing at SPDZ" found manually.

**Softball: protocol-layer fault injection.** Simulate a corrupt
party by injecting faults at the protocol level — corrupt shares,
MACs, Beaver triples, or messages during reconstruction. Check
whether the protocol aborts (correct) or silently produces a
wrong output (soundness bug). For malicious-secure protocols
(SPDZ, MASCOT), the oracle is binary. For covert protocols, the
oracle becomes a statistical hypothesis test over repeated runs.
For honest-majority Shamir protocols, the detection mechanism
depends on the threshold structure $(n, t)$, making party count
a meaningful parameter.

**Football: concurrency-aware testing.** The "Rushing at SPDZ"
bugs weren't logic bugs — they were race conditions and ordering
violations in the opening protocol (MAC checked after the value
was already used, thread-unsafe memory access). These only
manifest under specific interleavings. Instead of fuzzing inputs,
fuzz *schedules*: reorder messages, delay parties, interleave
threads. This is closer to concurrency testing (PCT, Cuzz) than
to traditional fuzzing, and nobody has applied it to MPC
implementations.

**The link:** the softball gives you *what* to corrupt; the
football gives you *when*. A fault that only causes a soundness
violation under a specific interleaving is a bug neither approach
finds alone.

---

# Softball — protocol-layer fault injection

Methodology is an Arguzz port; this section keeps the
divergences explicit.

## Methodology (from Arguzz, arXiv 2509.10819)

Arguzz fuzzes zkVM provers by **mutating instruction semantics
at the bytecode-dispatch layer**, not at the cryptographic
abstraction. The oracle is "verifier accepts mutated proof."
Operators: replace opcode (ADD→SUB, →NOP), replace operand
(constant, foreign register), skip instruction, corrupt branch
condition, corrupt memory value, corrupt address. Only executed
instructions are mutated. Prioritises hot paths.

**Port to MPC:** the corrupt-party set runs a mutated VM;
honest parties run clean. Oracle = "protocol did not abort AND
output ≠ honest-run output."

## Threat model

Malicious-MPC threat models tolerate up to $t$ Byzantine
parties, with the bound depending on the protocol family:

- **Dishonest majority** (SPDZ, MASCOT, SPDZ2k, BDOZ):
  $t \leq n-1$. Security holds as long as at least one party is
  honest.
- **Honest majority** (MaliciousShamir, Rep3, MaliciousRep3,
  Atlas, Rep4): $t < n/2$. The threshold structure $(n, t)$ is
  part of the security argument.

Each Byzantine party can only do one thing observable to honest
parties: **change the bytes it puts on the wire** (or fail to
send them). Internal computation, randomness, register state —
none of it matters to honest parties' view; they don't see it.

Wire-level menu (per Byzantine party):
- Send wrong bytes at a network round (corrupt share / MAC
  contribution / commitment / OT response).
- Send no bytes (refuse to participate → honest parties detect
  timeout, abort).
- Send late, after observing honest sends (rushing — defeated by
  commit-then-reveal where present).
- Send different bytes to different recipients (defeated by
  `Check_Broadcast` where present).
- Provide an adversarial input via INPUT.

That is the entire surface. Multi-party collusion lets the
Byzantine set coordinate these primitives across parties.
Bytecode-dispatch injection is a **convenient proxy** for
wire-level mutation: corrupting the share register before
OPEN's exchange phase produces the same network effect as
corrupting the wire bytes mid-round, with structured access to
"this is the share for value $v$ at PC $p$."

### Scoping decision: single corrupt party

This design restricts the Byzantine set to **one party**. Not
because the model demands it (it doesn't — see above), but for
tractability:

- Search space grows combinatorially with the size of the
  Byzantine set crossed with the operator catalog.
- Single-party deviation is already enough to express every
  Rushing-at-SPDZ-class bug we've seen.
- Multi-party collusion is the natural follow-up experiment
  (see Non-goals).

Wherever the prose below says "the corrupt party" (singular),
read it as "in our 1-corrupt scoping." The protocol is not
defined to have only one corrupt party.

## Two experiments, kept separate

The harness mixes two distinct experiments. Confusing them was
the source of half this design's earlier muddle.

**(E1) Attack simulation — the bug-finder.** Mutate the corrupt
party's wire-level outputs (operand corruption at OPEN-time, MAC
contribution corruption, message suppression). Run baseline +
mutated, twin-run output diff. Silent divergence = honest
parties accepted a real attack = real coverage gap in MP-SPDZ.

**(E2) Coverage-gap synthesis — the harness self-test.** Skip a
CHECK opcode locally on the corrupt party (or any other
purely-local instruction), creating a synthetic implementation
bug. Run an attack against it. If the harness *catches* the
synthetic bug (twin-run flags it), the harness works on this
bug class. If not, the harness has a blind spot. **E2 is not a
model of attacker behavior** — a Byzantine party can't
unilaterally suppress a multi-party check; honest parties still
run it and detect the missing contribution as a timeout. E2 is
"what if MP-SPDZ accidentally lacked a check here?" testing,
not "what can Carol do?" testing.

Different oracles, different yields, different roles. Run them
as separate harness modes.

## Why the VM layer, not the protocol layer

MP-SPDZ's bytecode is **protocol-agnostic** — the Compiler emits
one stream; `T::Protocol`, `T::MAC_Check`, `T::LivePrep` are
wired in at link time per share type. Patch the dispatch once →
every malicious protocol covered for free. Patching
`ProtocolBase::exchange` / `MAC_Check_Base` works too but
replicates logic per protocol family.

## Injection points

Primary: `Processor/Instruction.hpp:1530`, the opcode switch in
`Program::execute_with_errors`. Wrap opcode lookup with a
mutator.

Caveat: `ARITHMETIC_INSTRUCTIONS`, `CLEAR_GF2N_INSTRUCTIONS`,
`REGINT_INSTRUCTIONS` (macros expanded inline at 1532–1543)
bypass the default `Instruction::execute()`. Secondary shim:
mutate at register access (`Procp.get_S()[reg]` in
`Processor.hpp`) to cover arithmetic opcodes and memory-value
faults.

## Fault operator catalog

Three layers. Axes A and B are orthogonal; within axis A,
sub-axes A1 and A2 are complementary. Sequencing operators are
MPC-specific because checks are deferred and batched (zkVM
constraints are universal-per-transition; MPC checks are
selective-per-batch).

### Axis A — value mutations

Two sub-axes depending on granularity.

#### A1 — per-instruction operators (Arguzz import)

Per-PC mutations; each is expressible as a wire-level deviation.

1. **Corrupt operand at OPEN** — send wrong share contribution.
   Highest-priority; this is the canonical attack.
2. **Corrupt $\gamma_i$** — leave share intact, mutate MAC
   contribution. SPDZ-family only. Probes $(x_i, \gamma_i)$
   pairing across code paths.
3. **Operand foreign register** — substitute stale share before
   OPEN.
4. **Operand constant 0 / max** — boundary mutation.
5. **Replace opcode** — ADDS↔SUBS, MULS→ADDS, etc. Tests whether
   downstream checks notice the substitution.
6. **Corrupt stored share post-STMS** — write through state to a
   value opened later.

#### A2 — gadget insertion (primary mechanism)

Insert an arbitrary block of **local-only instructions** between
any two sync-points (MULS / OPEN / CHECK boundaries). The gadget
runs only on the corrupt party; honest parties see no extra
network traffic, so sync is preserved by construction.

Local-only opcode whitelist (no `Player` calls): ADDS, SUBS,
ADDSI, SUBSI, MULSI, MOVS, LDMS, STMS, clear arithmetic,
JMP, JMPNZ. Forbidden in gadgets: MULS, OPEN, INPUT, CHECK,
TRUNC_PR, DABIT, EDABIT.

Gadget templates:
- **Single-variable bump** — $s \leftarrow s + c$ for constant
  $c$. Degenerate; likely hits Wall 2 (MAC catches it).
- **Linear combination** — $s \leftarrow s + a \cdot t + b \cdot
  u$ for shares $t, u$ already in registers. Mixes secrets
  before opening.
- **Permute** — $s \leftrightarrow t$. Swaps two shares
  mid-computation; tests whether MAC checks are value-bound
  or position-bound.
- **Drift-and-restore** — $s \leftarrow s + \delta$, then
  $s \leftarrow s - \delta$. Net effect zero; exercises the
  accumulator window between the two opcodes.
- **Zero-and-recompute** — $s \leftarrow 0$; recompute $s$ from
  other registers. Tests whether the derived value propagates
  the corruption.

This is the "malicious party doing more work between sync points"
idea: the corrupt party executes extra locally-computed
operations that alter share state before it is opened.

### Axis B — sequencing (MPC-specific)

Inter-PC mutations on **local opcodes only** (no wire effect of
their own). These belong to E2 (coverage-gap synthesis), not to
attacker simulation — except where they correspond to a
missing-send (suppress contribution to a multi-party check).

7. **Skip a check** — drop CHECK, drop a sacrifice trigger,
   drop a MAC-accumulator push. Synthesises "what if this check
   were missing." Self-test only.
8. **Defer a check past consumption** — move CHECK after a
   downstream OPEN that depends on its accumulator. Tests
   whether other downstream protections still catch it.
9. **Reorder** — swap two non-communicating opcodes (e.g.,
   CHECK with a downstream local arithmetic op).
10. **Window** — insert local arithmetic between an OPEN and the
    CHECK that covers it; tests whether un-checked values
    propagate into output before the abort can fire.
11. **Cross-tape racing** — perturb thread interleaving to force
    orderings that violate accumulator/barrier invariants. The
    Rushing-at-SPDZ thread-race bugs live here. *Overlaps the
    football half — this is exactly the case the schedule-fuzz
    harness would explore systematically.*
12. **Skip a multi-party-check contribution** — the corrupt
    party fails to broadcast $\sigma$ at CHECK time. Wire-level:
    missing send. Honest parties should abort; if they don't,
    it's a real bug. (This one IS attacker simulation, not
    synthesis — the wire effect is real.)
13. **Branch flip on clear-register conditions** — JMPNZ/JMPI on
    a public value. Sync-safe (every party computes the same
    condition); the flip is local. Lowest priority.

### Excluded / Tier-2 (separate harness)

Operators that break the synchronisation invariant (skip MULS /
OPEN / RUN_TAPE on the corrupt party): honest parties hang.
These exit the soundness oracle and need a fairness/availability
oracle — different experiment, separate plumbing. Subclass:
skip-one-sync-fast-forward-to-next still deadlocks on the
finite-syncs argument; belongs in Tier-2.

## Synchronisation invariant

MP-SPDZ's network layer is async but **round counts and message
volumes must match** across parties, or honest parties hang. The
cut that matters is **sync-preserving vs sync-breaking**, not
values vs control flow.

**Sync-preserving (Tier 1, primary).** Anything that doesn't
change the network trace seen by honest parties.
- Value mutations on any opcode (axis A 1–6).
- Control-flow mutations on local-only opcodes (axis B 7–11, 13).
  The Rushing-at-SPDZ truncation bug is exactly a control-flow
  skip in this set — "values not calls" was the wrong shorthand.

**Sync-breaking (Tier 2, separate harness).** Skip / duplicate
any opcode that calls `Player::send` / `exchange` /
`Check_Broadcast`. Different oracle: "did the protocol's
identifiable-abort guarantee fire, or did honest parties hang
silently?"

**Whitelist is a claim, not a fact.** Some "local" opcodes flush
buffered network state (e.g., `MAC_Check::Check(Player)` does
broadcast). Derive the local-opcode list by grepping each
candidate handler in `Instruction.hpp` for `P.send` /
`P.exchange` / `P.Check_Broadcast` / Player calls. One-time
audit before writing the injector.

## Propagation filter

Most mutations are no-ops (value computed but never opened).
Build a **backward def-use slice** from every OPEN / CHECK /
PRIVATEOUTPUT over the bytecode — only PCs in the slice are
worth mutating. For axis-B operators, the interesting object is
a *pair* $(PC_\text{open}, PC_\text{check})$ or a *triple*
$(PC_\text{open}, PC_\text{consume}, PC_\text{check})$ — the
slice should also identify check-coverage relationships, not
just data flow. Dynamic taint-tracking is a more precise
fallback.

## Oracle

Twin-run with pinned randomness (PRNG seed + pre-generated
offline data reused across both runs):

- Baseline run: no mutation, record outputs and exceptions.
- Mutated run: one party's VM is patched, record outputs and
  exceptions.

Classification:
- `mac_fail` / `consistency_check_fail` in mutated run → protocol
  caught the deviation → **not a bug**.
- Mutated run succeeds, outputs differ → **soundness bug** (E1)
  or **coverage gap** (E2 on a check that turns out to actually
  be redundant — interesting but rare).
- Mutated run hangs / times out → Tier-2 territory; soundness
  oracle says "no signal."
- Segfault / assertion → liveness bug, triage separately.

Exception types in `Tools/Exceptions.h`. Abort call sites:
`Protocols/MAC_Check.hpp:197`, `Protocols/SecureShuffle.hpp:318`,
others.

## Party-role coverage (orthogonal concern)

The injector is symmetric; the harness iterates
$(\text{operator}, \text{corrupt\_party\_index})$ per protocol.
Symmetric families (SPDZ / MASCOT / SPDZ2k / MaliciousShamir):
one party index suffices. Role-asymmetric families need per-role
coverage:

- Rep3 / MaliciousRep3: `gen_player = 2, comp_player = 1`
  hardcoded (`Replicated.hpp:427`) — inject at 0, 1, 2.
- Astra: `gen_player = 0, comp_player = 1`
  (`Astra.hpp:445,480`) — inject at 0, 1.
- Trio: disjoint P0/P1/P2 roles in prep
  (`Trio.hpp:169,185,199`) — all 3.
- Dealer: last party is the dealer
  (`DealerInput.hpp:50`) — dealer + one non-dealer.
- Rep4: dynamic, but backup has extra check duty
  (`Rep4.hpp:118,131`) — all 4.
- Atlas: rotating king (`Atlas.h:29`) — one party if the run is
  long enough.

## Arguzz parallel — same class, three divergences

|                    | Arguzz (zkVM)                       | This project (malicious MPC)                |
|--------------------|-------------------------------------|---------------------------------------------|
| Cheater            | Prover                              | Byzantine party (set, scoped to 1 here)     |
| What they corrupt  | The execution trace they claim      | Bytes they send on the wire                 |
| Verifier mechanism | Constraints over the trace          | MAC check / RS reconstruction / sacrificing |
| Bug                | Constraints accept a wrong trace    | Honest parties accept output without abort  |
| Why bugs exist     | Constraint wrong / weak             | Check missing / weak / has coverage gap     |

Three divergences:
- **Coverage shape.** zkVM constraints are universal (every
  transition). MPC checks are selective (per opening). Bug
  distribution skews toward *missing* (not *weak*) on our side.
  Rushing-at-SPDZ examples are missing-class.
- **Cheater's freedom.** Arguzz prover lies about any
  transition. A Byzantine MPC party only lies about wire bytes.
  Strictly less freedom; smaller search space.
- **Sequencing dimension.** zkVM bugs are mostly per-instruction.
  MPC bugs are often *across* instructions (which check covers
  which open, in which batch). Axis B exists because of this.

Yield expectation: Arguzz-class. Handful of real bugs across
the malicious-protocol surface. Pitch is "systematic
differential fuzzer for malicious MPC implementations finds
Rushing-at-SPDZ-class bugs across all 30+ malicious protocols
MP-SPDZ ships." Not "we'll find new attacks on SPDZ."

## First concrete target

Reproduce the Rushing-at-SPDZ truncation bug:
1. **E2 self-test path:** in MP-SPDZ's TRUNC_PR, artificially
   excise the relevant check. Run a corrupt-share E1 mutation
   against the now-broken trace. Twin-run should flag silent
   divergence. If yes, harness works.
2. **E1 real-bug path:** without excision, sweep corrupt-share
   mutations across every OPEN in the test corpus. The TRUNC_PR
   opening should produce silent divergence on the affected
   MP-SPDZ versions; should be caught on patched versions.
   Confirms the harness rediscovers the real bug.

## Open questions

Determinism & oracle plumbing:
- Confirm MP-SPDZ supports pinned PRNG seeds and a reusable
  offline-data file.
- Inspect `Programs/Bytecode/*.sch`/`*.bc` format to confirm
  bytecode determinism across protocol choices.

Operator catalog:
- Audit which opcodes are truly local (no Player calls) vs.
  hidden-network — the axis-B whitelist depends on it.
- Decide whether the propagation-filter slice computation can
  reuse Compiler-emitted dependency information or needs to be
  rebuilt from bytecode.

Program generation & mutation (harness side):
- **How do we generate and mutate the input programs?**
  BabelFuzz's transforms are semantics-preserving; ours don't
  need to be — we're testing the protocol layer, not the
  compiler. But the transforms **must be local to the corrupt
  party**: they cannot change the network trace shape
  (round count, message volume per round) or honest parties
  hang. This is the synchronisation invariant restated as a
  constraint on the mutator. Define the local-mutation toolkit
  explicitly, distinct from BabelFuzz's metamorphic toolkit.
- Seed corpus: write minimal programs by hand, lift from
  MP-SPDZ's `Programs/Source/`, or borrow BabelFuzz's corpus?
- For axis B (sequencing), what's the right substrate to mutate
  on — `.bc` bytecode directly, the Compiler IR before
  emission, or in-memory `Instruction` objects after load?
  Trade-off is "easy to write" vs "easy to control PC mapping
  for the propagation filter."

Deployment / runtime switching:
- **How do we switch to the mutated program only on the
  Byzantine parties?** Options: (a) build two `.bc` files and
  point the corrupt party's `BaseMachine::load_schedule` at the
  mutated one; (b) load the same `.bc` everywhere and patch
  in-memory `Instruction` objects on the corrupt party post-load;
  (c) keep one `.bc` and inject at the dispatch wrapper using a
  per-PC mutation table the corrupt party reads from a sidecar
  file. (c) keeps one source of truth for round/sync structure;
  (a) is simplest to reason about. Pick before writing the
  injector.
- Do we need to rebuild MP-SPDZ with a fault-injection compile
  flag, or can the wrapper live as a runtime LD_PRELOAD /
  function-interpose? Compile-flag is simpler; LD_PRELOAD lets
  us run against unmodified binaries (matters for reproducing
  bugs on shipped releases).

## Non-goals

- FHE / ZK internals.
- Covert protocols as a primary target (cowgear, chaigear) —
  same surface as malicious, just with probabilistic detection.
- Semi-honest protocols — already covered by BabelFuzz (see
  related-work section below).
- **Multi-party collusion.** Within-threat-model but out of
  scope: the Byzantine set can be up to $n-1$ (dishonest
  majority) or $\lfloor (n-1)/2 \rfloor$ (honest majority), and
  exploring that crossed with the operator catalog is a
  strictly bigger search problem. Single-corrupt-party first;
  collusion as a follow-up experiment.
- Privacy bugs. Our oracle is output divergence; bugs where a
  Byzantine party *learns* something extra without affecting
  output are invisible to it.

---

# Football — concurrency-aware testing

**Status: scoped, not designed.** The hooks are in the softball
(axis-B operator 11, the synchronisation-invariant audit), but
there's no harness yet.

## Idea

Rushing-at-SPDZ's worst bugs were race conditions: MAC checked
after the value was already consumed; thread-unsafe accumulator
access. Input fuzzing won't find these — under a fixed schedule
they look correct. The bug only appears under an adversarial
interleaving.

**Schedule fuzzer.** Take a fixed program + fixed inputs. Vary
the *thread / message schedule*: which tape advances next, which
party's send arrives first, where context-switches fall inside
`MAC_Check::Check`, how the prep-buffer cursor races against
opening. Same correctness oracle as the softball: protocol
abort, or silent wrong output.

PCT (Burckhardt et al.) and Cuzz are the references — randomised
schedulers with probabilistic guarantees on hitting bugs of
bounded depth $d$. Adapting them to MP-SPDZ means hooking the
pthread layer (`Processor/Machine.hpp`) and the network send
points (`Networking/Player.h`) to insert controlled delays /
forced reorderings.

## What to build (TBD)

- Instrument `Player::send` / `Player::exchange` /
  `Check_Broadcast` to be schedulable.
- Hook the per-tape pthreads to be steppable.
- Define a schedule-perturbation operator set (delay one party
  $k$ rounds; swap message arrival order; interleave thread A
  one step before thread B's barrier).
- Same twin-run oracle: silent divergence vs. caught abort.

## Why this is its own thing

The softball's axis B has the cross-tape-racing operator (#11),
but it's a single coarse knob. The football would expose the
schedule itself as the search space, with a proper exploration
strategy.

---

# Related work: BabelFuzz

Watzinger, Wüstholz, Garg, Christakis. *Cost-Effective Testing of
MPC Compilers.* PACMSE Vol. 3, FSE-2026, Article FSE199.
[Paper](https://mariachris.github.io/Pubs/FSE-2026-MPC.pdf).
[Tool](https://github.com/Rigorous-Software-Engineering/BabelFuzz).

## What it does

Differential / metamorphic fuzzing of **MPC compilers** (not
protocols). Generates programs in an expressive IR, translates
them to multiple MPC DSLs (MP-SPDZ, EMP Toolkit, EzPC, Silph)
**and** to plain Python. Runs each translation, compares
outputs.

- **DT mode:** the Python translation is the oracle. Any
  divergence between an MPC compiler's output and the Python
  output is a logic bug in the MPC compiler.
- **MT mode:** apply semantics-preserving transformations to the
  IR; outputs of original and transformed programs should match.

## Threat model

**Semi-honest only.** From §5.2 (verbatim): *"we choose
comparatively fast (i.e., semi-honest) protocols for the actual
execution of MP-SPDZ programs."* Every run is all-honest. No
party deviates.

## Bugs found

27 unique logic bugs across the four compilers (15 fixed). All
are compiler/optimizer bugs: optimizer dropping write-after-write
dependencies, sfix/cfix shallow copies, loop unrolling skipping
iterations, fixed-point NaN, bit-shift/division of negatives.
**Zero touch malicious-security code paths.**

## The gap our project fills

BabelFuzz tests the **Compiler box** of the architecture map
under all-honest execution. We test the **Protocol box** under
Byzantine deviation.

| Axis           | BabelFuzz                     | This project                                  |
|----------------|-------------------------------|-----------------------------------------------|
| SUT layer      | Compiler (Python → bytecode)  | Protocol layer at the EXEC↔PROTO seam         |
| Threat model   | All-honest                    | Byzantine (scoped to 1 party here)            |
| Mutation       | Source program / IR           | Bytecode dispatch on a corrupt party          |
| Oracle         | MPC output vs. Python output  | Twin-run output diff under pinned randomness  |
| Bug class      | Optimizer / type bugs         | Missing / weakened malicious-security checks  |
| What signals   | Numerical divergence          | Silent divergence without `mac_fail` / abort  |

Orthogonal. BabelFuzz strengthens our positioning: there's now
a published completeness fuzzer for MPC, and it explicitly punts
on malicious security.

## Composability

BabelFuzz's seed corpus is exactly what we'd want to fault-inject
into — diverse opcode coverage, well-defined semantics. "Use
BabelFuzz seeds, run them under malicious protocols with a
party's dispatcher mutated" is a defensible plan if upstream
cooperation is feasible.
