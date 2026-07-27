#!/bin/bash
ROOT="$(git rev-parse --show-toplevel)" || {
  echo "not inside a git repo" >&2; exit 1;
}
touch "$ROOT/.claude/.new_problem"
rm -f "$ROOT/.claude/guess.md"
echo "new problem marked at $(date)"
