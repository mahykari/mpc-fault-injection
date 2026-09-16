---
name: project_session_state_2026_09_16
description: 2026-09-16 — PR #6 merged; claude-md worktree made; next is CLAUDE.md branch, then the big refactor on master, then matrix-rewrites merge
metadata:
  type: project
---

**Done 2026-09-08 to 2026-09-16.**
- All 46 inline review comments on PR #6 answered in-thread, plus a top-level
  reply on coins and argument soups.
- The cheap half of the review landed as `70c42dc`; PR #6 merged to master as
  `fa4651a` on 2026-09-16. `BACKLOG.md` (repo root) is now the task backlog;
  Mahyar refused GitHub Projects.
- Worktree `/home/mkarimi/claude-md`, branch `claude-md` off master, for the
  CLAUDE.md changes. `CLAUDE.local.md` copied in; no `.venv` there.
- Main checkout `/home/mkarimi/mpc-fault-injection` switched to `master`.

**Plan, in order (Mahyar's, 2026-09-16).**
1. DONE 2026-09-16 (branch `claude-md`, pending merge). CLAUDE.md branch: loosen the terseness rules that produce tangled code, add
   the design rules the review established. See [[feedback_bel_canto_for_design]].
   Also drop teaching mode and the contractor machinery ("I'm mostly in
   contractor mode"): the CLAUDE.md "Teaching mode" section,
   `.claude/agents/contractor.md`, hooks `contractor-start.sh`,
   `contractor-stop.sh`, `edit-gate.sh` (guess.md gate), command
   `new-problem.md` + `scripts/new-problem.sh`, and their entries in
   `.claude/settings.json`. Keep librarian, notify, turn-start, mpc-explore.
2. Big refactor on master, deadline "a fraction of a month" (a report to his
   boss). Purpose is also for him to learn the architecture all the way down
   and interfere in its design: walk module by module, he decides keep/kill/
   rename, and `BLUEPRINT.md` gets rewritten to match. Scope:
   [[project_matryoshka_configs]], `store.py` rewrite
   ([[project_next_task_in_memory_queue]]), deleting `aggregate`/`rerun-inert`/
   `results.db`. Land it as a sequence of small merges, one doll at a time.
3. Merge `matrix-rewrites` through its own merge list (`PROGRESS.md` there).

**Why this order:** the matryoshka touches `config.py`, `__init__`/`run.py`,
generator, injector, oracle, executor; every one of matrix-rewrites' 17 commits
touches those too. Refactor first, merge across it once.

**Open from the review, deliberately:** the three `store.py` threads, the
planner's `--rng-seed` (per-point corrupt set and depth), and the last soup hop
`ExperimentConfig` into `Config` via `dataclasses.replace`.

**Gotcha, fixed 2026-09-16:** `link-memory.sh` used to link only the MAIN
worktree's slug, so other worktrees (matrix-rewrites) ran without repo memory.
It now links the cwd worktree's slug to that worktree's own `.claude/memory`.
Run it once in every new worktree, including the refactor one.
