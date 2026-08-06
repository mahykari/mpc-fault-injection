---
name: project_first_campaign_baseline
description: First full 50k MASCOT campaign result — the stock-patched baseline to compare seeded-bug runs against
metadata: 
  node_type: memory
  type: project
  originSessionId: a26058fb-6cc7-452a-8afa-8b21c7479a2f
---

First full campaign on mercury (2026-06-17): 10 instances × 5000 runs = 50,000, stock patched MASCOT (no seeded bug), ~20 min wall, ~224 ms/run.

Verdict spread:
- caught 41,089 (82.2%) — MAC check fired
- inert 8,890 (17.8%) — output matched honest; the bucket whose true-inert-vs-active-but-masked ambiguity is unresolved (the Semi dry-run idea would re-examine these)
- aborted 15, honest_invalid 6 (noise floor)
- **bug 0, error 0**

Noise floor (the 21 aborted+honest_invalid) investigated 2026-06-17 and resolved as **transient, not real**: re-running all 21 host-side in isolation at their correct per-instance depths (depths recomputed from launch.py `instance_depths(10, seed=0)`; reproduction needs the per-instance depth, not just the seed) all completed in ~100-200ms → 18 caught + 3 inert, zero hangs. So the stalls are coupled to the parallel containerized run (port/netns race or contention), not the programs. `timeout_s=30` acted as a flakiness filter. Corrected spread: caught 41,107 / inert 8,893 / bug 0. Fix options: retry-once-on-timeout in the instance loop (pragmatic) vs root-cause the container-path stall on mercury.

This is the **baseline**: on sound MASCOT, bug=0 is the correct result. Validation is running the seeded-bug binary (`seeded_bug_binary=True`) and confirming bug jumps off zero. See [[project_find_vs_seed_axes]].

Gotcha when aggregating from the log: `honest_invalid:` has no space before its colon (label is exactly 14 chars), so a `\s+:` regex silently drops it. Verdict categories are log-only — `report.json` stores raw RunResult, not the verdict (see the reporter persistence gap).
