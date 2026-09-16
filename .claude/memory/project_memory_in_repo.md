---
name: project_memory_in_repo
description: "Project memory lives in the repo at .claude/memory/, symlinked from ~/.claude by link-memory.sh; run once per machine"
metadata: 
  node_type: memory
  type: project
  originSessionId: d937afb8-b804-48f4-98b3-cfaebe21cddc
  modified: 2026-08-06T13:24:27.589Z
---

Set up 2026-08-06. Memory is **tracked in the repo** at `.claude/memory/`. The harness derives its memory path from the cwd (`~/.claude/projects/<abs-path-with-slashes-as-dashes>/memory`), so every machine and worktree gets a different slug and would otherwise start empty.

`.claude/scripts/link-memory.sh` symlinks that slug path at the **main worktree's** `.claude/memory` (resolved via `git rev-parse --git-common-dir`, so a branch checkout doesn't fork the memory). Idempotent; **run it once per machine**. It moves any existing real dir to `memory.bak`.

Consequences:
- Memories are ordinary tracked files. They sync by `git pull` / `git push`; conflicts land in `MEMORY.md` and merge like anything else. Both machines commit their own.
- **The repo is public**, so everything here is world-readable. The user accepted this knowingly. Don't write anything into memory you wouldn't publish.
- `.claude/contractor`, `.claude/guess.md`, `memory.bak/` are gitignored local-only state.
- **Memory is branch-dependent.** Check out a branch older than the merge that introduced `.claude/memory/` and the symlink target goes empty. Merge master into a branch before working on it.

mercury was linked 2026-08-06: its `~/mpc-fault-injection` was converted from an rsync copy in place (`git init`, `remote add`, `fetch`, `reset origin/<branch>`), and it has a GitHub deploy key with write access.

This is what made [[project_mercury_deploy]] rsync-free.
