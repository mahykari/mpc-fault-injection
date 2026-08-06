#!/bin/bash
# Point this machine's Claude memory dir at the repo's .claude/memory, so
# memories travel by git like everything else. Run once per machine. Idempotent.
#
# The harness derives the memory path from the cwd, so every machine (and every
# worktree) gets its own slug. We always link to the MAIN worktree's copy, so a
# branch checkout doesn't fork the memory.
set -euo pipefail

COMMON="$(git rev-parse --path-format=absolute --git-common-dir)" || {
  echo "not inside a git repo" >&2; exit 1;
}
ROOT="$(dirname "$COMMON")"
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
