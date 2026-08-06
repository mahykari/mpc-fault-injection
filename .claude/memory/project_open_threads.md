---
name: project_open_threads
description: Live threads after the first 50k campaign — pick up here next session
metadata: 
  node_type: memory
  type: project
  originSessionId: a26058fb-6cc7-452a-8afa-8b21c7479a2f
---

State as of 2026-06-17 EOD (first full 50k MASCOT campaign done, see [[project_first_campaign_baseline]]):

**Git/deploy (user does pushes/PRs manually — [[feedback_user_drives_button]]):**
- master has 2 local **unpushed** commits: per-run wall timing, and the Containerfile COPY-circil flip (build needs no GitHub key).
- PR #3 (worktree-parallel-runs) still **open** on GitHub — merged locally, not closed.
- Deployed + running on mercury at `~/mpc-fault-injection` (rsync `-az`, excludes .venv/MP-SPDZ/runs/.git/.claude). mercury = 94c/192t, 1.5TB; box is effectively the user's alone.

**Open work threads:**
1. **Semi dry-run to disambiguate `inert`.** ~8,893 inert cases ride on "output matched honest = no-op," which can't distinguish truly-inert from active-but-masked. Re-run MASCOT-`inert` cases under semi-party.x (no checks) as defense-free ground truth: Semi diverges → active deviation that escaped → escalate; Semi matches → truly inert. Gate on inert-only to keep it cheap. semi-party.x already in distro.
2. **Reporter persistence gap.** `report.json` stores raw RunResult, NOT the verdict category — verdicts are stdout/log-only. Make reporter write verdicts (bugs.jsonl/passes.jsonl per its own docstring) + a campaign rollup over runs/, so "which summary" has a disk-backed answer.
3. **Retry-on-timeout** in the instance loop to auto-absorb the transient noise floor.
4. **Seeded-bug validation run** — run seeded_bug_binary=True campaign; confirm bug jumps off zero (the other half of the harness proof). See [[project_find_vs_seed_axes]].
