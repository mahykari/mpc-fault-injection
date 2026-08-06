---
name: project_party_count_grid
description: Campaign spreads protocol x party-count; shamir even-n verified fine; runs labeled by n_parties
metadata: 
  node_type: memory
  type: project
  originSessionId: db3d86a0-5d48-40b3-8aa5-55b9590cdbf6
---

The continuous campaign runs a **(protocol × party-count) grid** (2026-07-09, commit `53f683e`). `containers/continuous.py --protocols ... --party-counts 3,5,7,9` crosses the two into combos, spread round-rotated across the 16 instances (rotation matters when combos > instances — `combos[(i+round_idx)%len]`). Corrupt set auto-sized per threshold: dishonest (mascot/spdz2k) t=n−1, honest-majority (shamir) t=⌊(n−1)/2⌋ via `spec.max_corrupt(n)`. Every run is labeled by `n_parties` (new `results.db` column + Report field, mirrors [[project_shamir_ssl_gap]]'s protocol column; idempotent ALTER migration in `cmd_aggregate`).

**Shamir even-n is fine — no parity constraint.** Verified against MP-SPDZ source (mpc-explore): the only gates are `2t < n` (`ShamirOptions.cpp:64`, a runtime throw) and `n >= 3` (`ShamirOptions.cpp:45`); default threshold is `⌊(n−1)/2⌋` (`ShamirOptions.cpp:57`), which always satisfies `2t<n`. So n = 3..9 all run for every protocol; don't special-case odd/even. Smoke-confirmed: mascot/spdz2k/shamir all `caught` at n=9, shamir `caught` at even n=4 and n=6.

The pipeline was already fully n-parameterized (execution layer *and* program/input side — inputs are baked constants `sint(idx+1)`, not per-party secret inputs), so this needed no pipeline plumbing, just the continuous.py spread + the DB label. Raising n adds parties running the protocol, NOT input-providing parties.
