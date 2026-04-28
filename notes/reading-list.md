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
