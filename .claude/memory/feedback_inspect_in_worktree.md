---
name: feedback_inspect_in_worktree
description: "To review a branch's changes, read files in its own worktree; don't run merge-tree/merge-sim from master."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: db3d86a0-5d48-40b3-8aa5-55b9590cdbf6
---

To take a close look at an unmerged branch, `cd` into its worktree (`.claude/worktrees/<name>/`) and read the files in place. Do NOT run `git merge-tree` / `git merge --no-commit` conflict-sims from master to reason about it — the user called that "mergin shit like shit be all nice and isolated," i.e. pretending overlapping parallel work is clean when it isn't.

**Why:** branches here are developed in parallel worktrees and overlap the same files (config.py, main.py, types.py). A "CLEAN" from merge-tree hides semantic collisions; reading the real code in the worktree is the honest look. User also wants to do the git-chops themselves — hand them the commands ([[feedback_suggest_dont_write]]), don't auto-run merges ([[feedback_user_drives_button]]).

**How to apply:** `git worktree list` → open the branch's dir → Read the changed files there. Only merge when the user greenlights, and never present a from-master merge-sim as proof of isolation.
