#!/bin/bash
# Point this machine's Claude memory dir at the repo's .claude/memory, so
# memories travel by git like everything else. Run once per worktree. Idempotent.
#
# The harness derives the memory path from the cwd, so every machine (and every
# worktree) gets its own slug. Each slug links to ITS OWN worktree's copy, so
# what a session reads is exactly what that branch commits; branches sync
# memory by ordinary merging.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)" || {
  echo "not inside a git repo" >&2; exit 1;
}
SLUG="${ROOT//\//-}"
TARGET="$HOME/.claude/projects/$SLUG/memory"

if [ -L "$TARGET" ] && [ "$(readlink -f "$TARGET")" = "$ROOT/.claude/memory" ]; then
  echo "already linked: $TARGET"
  exit 0
fi

mkdir -p "$(dirname "$TARGET")"
if [ -e "$TARGET" ] && [ ! -L "$TARGET" ]; then
  [ -e "$TARGET.bak" ] && {
    echo "$TARGET.bak already exists; move it aside first" >&2; exit 1;
  }
  mv "$TARGET" "$TARGET.bak"
  echo "moved existing memory dir to $TARGET.bak"
fi

ln -sfn "$ROOT/.claude/memory" "$TARGET"
echo "linked $TARGET -> $ROOT/.claude/memory"
