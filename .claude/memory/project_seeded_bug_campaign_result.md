---
name: seeded-bug-campaign-result
description: Result of the 80k 8-combo Check()-toggling seeded-bug campaign on mercury
metadata: 
  node_type: memory
  type: project
  originSessionId: e05c0f57-d00f-4f62-9f65-1a3f6654a644
---

Ran the 8-combo × 10k seeded-bug campaign (80k runs, ~13 min) on **mercury** (mkarimi@mercury.se.tuwien.ac.at) 2026-06-29. Results in mercury:~/mpc-fault-injection/runs/results.db (79997/80000; 3 crashed pre-report). Followup to [[seeded-bug-campaign-prep]].

**Finding:** bugs (silent wrong output) surface ONLY when BOTH `subprocessor_check` and `beaver_check` are disabled (~8.2k bug / ~10k each; caught drops to 0). Any single check on → all deviations caught, 0 bug. `private_output_check` has zero effect in any combo. Baseline clean (0 bug). The ~8217 caught / ~1780 inert split is stable across every check-on combo, so the disabled pair fully accounts for the verdict shift.

**Why it matters:** clean validation that the harness catches corrupt-party deviations when the malicious-security checks are on, and they slip silently when the right check pair is off.
