---
name: project_campaign_disk_blowup
description: 2026-08-05 campaign died at 15% on a full disk; MP-SPDZ Memory-p-P dumps were the cause
metadata:
  type: project
---

The 2M-run campaign (`runs/campaign.db`, launched 2026-08-04) was terminated
2026-08-06 with `/home` at 93%. 304,669 of 1,992,000 experiments completed.

Verdicts: caught 250,443 (82.2%), inert 54,093 (17.8%), honest_invalid 105,
aborted 28, **bug 0**. Same 82/18 split as the 50k baseline in
[[project_first_campaign_baseline]], now at 25x the samples.

Grid coverage was lopsided: mascot n=3 finished, mascot n=5 reached 84%,
and spdz2k / malicious-shamir / n=7 / n=9 got zero runs. The queue is served
in id order, so one protocol ate the whole disk. See [[project_party_count_grid]].

Root cause of the 1.1T: MP-SPDZ writes `Player-Data/Memory-p-P<i>` at
**836K per party per side** on every run. A caught run pays n x 836K (mutated
aborts before writing), an inert run pays 2n x 836K. Average 3.6M per run
against ~1K of actual signal; `report.json` is 614 bytes and the DB row is
smaller. Nothing in `pipeline/` or `containers/` ever deletes a run dir.

The campaign could never have finished: 1.99M x 3.6M is ~7.2T on a 3.5T disk.

Run dirs were deleted wholesale (Mahyar judged them not worth keeping);
`campaign.db` and the archived DBs were preserved. Deleting ~2M inodes with a
single `rm -rf` was slow; 16-way parallel `rm` partitioned by the `i00`-`i15`
instance prefix was roughly 10x faster on this ext4-on-SSD box.

**Fixed 2026-08-06**: the party binaries take `-o no_memory_output`, which
skips the dump at `Processor/Machine.hpp:647`. Added to the argv in
`pipeline/mpspdz.py`. Smoke-tested: a caught mascot n=3 run went from ~2.5M to
68K, zero `Memory-*` files, verdict unchanged. `-o` is a comma-separated
free-form list and unknown entries are ignored, so it is safe across protocols.

Still unaddressed: nothing deletes a run dir. At 68K a 2M-run campaign is
~136G, tolerable, but the dirs still accumulate with no retention policy.
