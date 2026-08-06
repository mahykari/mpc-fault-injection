---
name: project_find_vs_seed_axes
description: "Two separate axes — bugs we can FIND (real, via corrupt-party deviations) vs bugs we SEED (plant to validate the harness). Don't conflate."
metadata: 
  node_type: memory
  type: project
  originSessionId: 0e5d5f98-876f-42bd-a721-faa66a6f6eeb
---

Two distinct things, not one capability ladder:

- **Finding** = the actual fuzzing. Inject a corrupt-party *deviation* (a real adversary move: gadget on the online tape, cheat in preprocessing contributions, cheat at sacrifice, race under concurrency) and see if an *existing* missing/weak check in MP-SPDZ lets it through. The MP-SPDZ **types** (sfix, sfloat, sbitvec, Array/Matrix batch-open, personal) are the primary instrument here — they widen which code paths a deviation reaches. sfix is highest-signal: its multiply ends in trunc_pr, the `reveal(check=False)` truncation path. On a buggy build, sfix is a tier-0 *find* of the truncation bug — no flag-flip needed.

- **Seeding** = harness validation. Deliberately plant a known bug (flip a `check=` flag, weaken a C++ check) on a *fixed* build, confirm twin-run flags it. NOT something a corrupt party can do; it tests the detector, not MP-SPDZ. This is the seeded-bug binary line of work [[project_patched_binary_done]].

**Why:** I wrote a single tier-0..5 "capability ladder" in notes/historical-bugs.md that mixed adversary-cheats (finding) with code-modifications (seeding) and implied "climb to find more bugs" — wrong for the seeding rungs.

**How to apply:** When discussing reach, separate "where can a corrupt party deviate" (find) from "what bug do we plant to validate detection" (seed). CHECK-flag flip and C++ mutation are seeding, not finding. See [[feedback_injector_surfaces_not_creates]].
