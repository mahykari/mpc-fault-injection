#!/bin/bash
# contractor-stop.sh - SubagentStop hook, matcher: contractor
rm -f "$CLAUDE_PROJECT_DIR/.claude/.in-contractor"
exit 0
