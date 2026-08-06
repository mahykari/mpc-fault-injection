---
name: session-2026-06-29
description: "Multi-agent session — retry, semi-rerun, protocols features + 80k seeded-bug campaign; pick up with merges + smoke-test"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6187cd17-c847-47f6-b0a5-f493756d85d5
---

Session 2026-06-29: four-agent parallelism + 80k campaign on mercury.

## Completed

- **retry** (`worktree-agent-a13463147246594a1`, 31f8ea4) — retry aborted runs up to 2×. Beta-reviewed, fixes applied.
- **semi-rerun** (`worktree-agent-a070b81732aa6d16b`, b80ec01) — `rerun-inert` subcommand, re-runs inert verdicts under semi-party.x to distinguish active-but-masked vs truly-inert. Beta-reviewed, instance_id bug fixed.
- **protocols** (`worktree-more-protocols`, 7eead0a) — ProtocolSpec table for spdz2k + malicious-shamir. PR #5 created. Beta-reviewed, cleanups applied.
- **80k seeded-bug campaign** — 8 Check()-toggle combos × 10k runs on mercury. Results: bugs ONLY when subprocessor_check AND beaver_check both disabled (~8.2k bugs). private_output_check has no effect. `runs/results.db` pulled back (12.6 MB, 79,997 rows).

## Not merged yet

1. `worktree-agent-a13463147246594a1` (retry) — ready to merge to master
2. `worktree-agent-a070b81732aa6d16b` (semi-rerun) — ready to merge to master
3. `worktree-more-protocols` (PR #5) — blocked on smoke-test

## Blocked on your button

- `./containers/build.sh patched` — builds patched spdz2k-party.x + malicious-shamir-party.x
- Then smoke-test:
  ```
  CONFIG='{"protocol":"spdz2k","n_parties":3,"malicious_parties":[0,1],"seeds":[0,1,2]}' uv run python main.py run
  CONFIG='{"protocol":"malicious-shamir","n_parties":3,"malicious_parties":[0],"seeds":[0,1,2]}' uv run python main.py run
  ```
- After smoke-test passes, merge PR #5

## Campaign headline

subprocessor+beaver = the load-bearing pair. Either check alone → 0 bugs, all caught. private_output_check is inert (no effect in any combo).
