# Reading list

Only read what you need, when you need it. Each entry says WHY
and WHEN.

## Already absorbed (background)

### Damgård, *The SPDZ Protocol* — Bar-Ilan Winter School 2015 (partial: through "discount" broadcast)
- **Slides:** https://cryptobiu.github.io/assets/wp-content/13.pdf
- **Talk:** https://youtu.be/N80DV3Brds0
- **Covered (watched):** Beaver triples; SPDZ MAC $m(x) = \alpha x$
  and its security game; $[x]$ and $[[x]]$ representations;
  opening protocol (the $d_1 + d_2 = 0$ check); batch MAC check
  via random linear combination (= what `MAC_Check.h` actually
  does); commitments via $[[r]]$; $O(n^2) \to O(n)$ opening;
  "discount" broadcast.
- **Not yet watched:** SHE-based preprocessing — ZK proofs of
  plaintext knowledge, distributed decryption, MAC generation,
  triple sacrificing. Pick this up if/when preprocessing becomes
  load-bearing for the design.

### Rushing at SPDZ (ePrint 2025/789)
- **URL:** https://eprint.iacr.org/2025/789
- **Why it matters here:** Ground truth for what bugs exist —
  missing MAC checks, thread races. The truncation/MAC-check
  attack is the first concrete target for the harness.

## Read now (before next meeting)

### Arguzz (arXiv 2509.10819)
- **URL:** https://arxiv.org/abs/2509.10819
- **Why:** The methodology we're porting. Mutate instruction
  semantics at the bytecode-dispatch layer; check whether the
  verifier still accepts. Our oracle is the MPC analogue.
- **Focus:** §3 (methodology), Appendix B (operator grammar),
  §4 + Table 1 (bug patterns).

## Read only if a specific protocol comes up

### SPDZ paper (Damgård, Pastro, Smart, Zakarias 2011)
- **URL:** https://eprint.iacr.org/2011/535
- **Why:** When the slides aren't enough and you need the formal
  MAC/opening protocol details.

### MASCOT (Keller, Orsini, Scholl 2016)
- **URL:** https://eprint.iacr.org/2016/505
- **Why:** OT-based triple generation + sacrificing + OT
  correlation checks. Read when looking at MASCOT triple
  verification code.

### MP-SPDZ paper (Keller 2020)
- **URL:** https://eprint.iacr.org/2020/521
- **Why:** Architecture of the VM and how protocols plug in.
  Read if the code structure stops making sense.

## Don't read

- FHE internals (Regev, BFV, TFHE) — only matters if FHE
  becomes the project
- ZK papers — Circuzz/Arguzz already covers it
- Compiler-testing surveys — already absorbed
