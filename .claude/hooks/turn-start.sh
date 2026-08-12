#!/usr/bin/env bash
# .claude/hooks/turn-start.sh
#
# UserPromptSubmit hook. Records when the current turn began so notify.sh
# can decide whether the turn ran long enough to be worth a ping.
#
# Always exits 0.

set -uo pipefail

cat >/dev/null 2>&1 || true

DIR="${CLAUDE_PROJECT_DIR:-.}/.claude"
mkdir -p "$DIR" 2>/dev/null || exit 0
date +%s > "$DIR/.turn-start" 2>/dev/null || true

exit 0
