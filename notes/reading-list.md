# Reading list

Only read what you need, when you need it.
Each entry says WHY you'd read it and WHEN.

## Read now (before next meeting)

### Rushing at SPDZ (ePrint 2025/789)
- **URL:** https://eprint.iacr.org/2025/789
- **Why:** Shows real attacks on MP-SPDZ and SCALE-MAMBA.
  Missing MAC checks, thread race conditions, rushing attacks.
  This is the "ground truth" for what kinds of bugs exist.
- **What to focus on:** Sections describing the actual attacks,
  not the formalism. Look at their Figures 5–7.

### Arguzz (arXiv 2509.10819)
- **URL:** https://arxiv.org/abs/2509.10819
- **Why:** This is the methodology we're porting. Fault-injects zkVM
  provers by mutating instruction semantics at the bytecode-dispatch
  layer and checks whether the verifier still accepts. Our oracle is
  the MPC analogue (protocol abort vs silent wrong output).
- **What to focus on:** §3 "Arguzz Methodology" (injection types,
  algorithm). Appendix B "Arguzz Injection Types" (full operator
  grammar). §4 + Table 1 (bugs found — pattern matters more than
  specifics).

## Foundational classics — base mechanisms

Read these before reasoning about specific protocols. The MAC scheme, sacrificing, RS reconstruction, and Beaver triples all build on these.

### Shamir, *How to Share a Secret* (1979)
- **URL:** https://dl.acm.org/doi/10.1145/359168.359176
- **Why:** Threshold secret sharing via polynomial interpolation. Underpins MaliciousShamir, BGW, Atlas, and the RS-error-detection angle for honest-majority malicious protocols.
- **When:** Before reading any honest-majority code in MP-SPDZ.

### Beaver, *Efficient Multiparty Protocols Using Circuit Randomization* (Crypto 1991)
- **URL:** https://link.springer.com/chapter/10.1007/3-540-46766-1_34
- **Why:** Beaver triples — the multiplication primitive used by virtually every dishonest-majority protocol. Both SPDZ and MASCOT preprocess a stash of triples and use this exact protocol online.
- **When:** Before reading anything that talks about "triple," "muls," or `Beaver*` in MP-SPDZ.

### Ben-Or, Goldwasser, Wigderson (BGW), *Completeness Theorems for Non-Cryptographic Fault-Tolerant Distributed Computation* (STOC 1988)
- **URL:** https://dl.acm.org/doi/10.1145/62212.62213
- **Why:** Honest-majority malicious MPC over a finite field with information-theoretic security, using Reed-Solomon error detection during reconstruction. The deterrence mechanism for MaliciousShamir is BGW-shaped.
- **When:** When looking at MaliciousShamir reconstruction code or thinking about (n, t) thresholds.

### Damgård, Keller, Larraia, Pastro, Scholl, Smart, *Practical Covertly Secure MPC for Dishonest Majority — or: Breaking the SPDZ Limits* (ESORICS 2013)
- **URL:** https://eprint.iacr.org/2012/642
- **Why:** The **batched MAC check** protocol — random linear combination, commit-then-reveal — that's what MP-SPDZ's `MAC_Check.h` actually implements. The 2012 SPDZ paper introduces the MAC scheme; this one is the protocol-as-engineered.
- **When:** When reading `MAC_Check.h` / `MAC_Check.hpp` and trying to match `Check(Player&)` to a paper.

## Read if you need to understand a specific protocol

### SPDZ protocol (Damgård et al., 2012)
- **URL:** https://eprint.iacr.org/2011/535
- **Why:** If you need to understand how MAC checks work in SPDZ.
  The MAC key α, the share representation [x] = (x_i, γ_i(x)),
  the batch opening protocol.
- **When:** When you're looking at MAC_Check.h in MP-SPDZ
  and can't figure out what it's doing.

### MASCOT (Keller et al., 2016)
- **URL:** https://eprint.iacr.org/2016/505
- **Why:** OT-based triple generation with malicious security.
  Explains amplifying, sacrificing, OT correlation checks —
  the things that Semi* strips out.
- **When:** When you're looking at the Beaver triple verification code.

### Malicious Shamir (honest majority)
- **Why:** If the Shamir angle (varying n, t) becomes relevant.
  Reconstruction with error detection.
- **When:** When you're looking at MaliciousShamir* in MP-SPDZ.
- **Background:** Lindell's MPC tutorial (which you already know)
  covers Shamir basics.

### MP-SPDZ paper (Keller, 2020)
- **URL:** https://eprint.iacr.org/2020/521
- **Why:** Architecture overview of MP-SPDZ itself.
  How the VM works, how protocols plug in, how the compiler works.
- **When:** If the code structure doesn't make sense from reading alone.

## Don't read (unless the project goes there)

- FHE papers (Regev, BFV, TFHE) — only if the FHE track becomes your project
- ZK papers — already covered by Circuzz/ARGUZZ, not your problem
- General compiler testing surveys — you've already absorbed the key ideas
  from reading the three papers
