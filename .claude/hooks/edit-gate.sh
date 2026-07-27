#!/bin/bash
# edit-gate.sh - PreToolUse hook for Edit|Write
# Main thread: block edits unconditionally.
# Contractor subagent: allow only if guess.md is newer than .new_problem.

DIR="$CLAUDE_PROJECT_DIR/.claude"

# contractor-mode override (teaching mode off)
[ -f "$DIR/contractor" ] && exit 0

# not inside a contractor subagent -> main thread -> no edits, ever
if [ ! -f "$DIR/.in-contractor" ]; then
  echo "Blocked: main thread never edits. Teaching dialogue only." >&2
  echo "Spawn a contractor subagent after Mahyar has written his guess." >&2
  exit 2
fi

# inside contractor: require a guess for THIS problem
if [ ! -f "$DIR/guess.md" ]; then
  echo "Blocked: no guess.md. Ask Mahyar for his written guess first." >&2
  exit 2
fi

if [ -f "$DIR/.new_problem" ] && [ "$DIR/guess.md" -ot "$DIR/.new_problem" ]; then
  echo "Blocked: guess.md is older than the current problem." >&2
  echo "Mahyar must write a fresh guess (or run /new-problem was forgotten)." >&2
  exit 2
fi

exit 0
