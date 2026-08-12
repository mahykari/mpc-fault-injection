#!/usr/bin/env bash
# .claude/hooks/notify.sh
#
# Sends a Discord webhook ping.
#
# Usage:
#   notify.sh "message"           always sends
#   notify.sh --gate "message"    sends only if the turn ran longer than
#                                 NOTIFY_MIN_SECONDS (default 300)
#
# Env:
#   DISCORD_WEBHOOK_URL   required; exit 0 silently if unset
#   DISCORD_USER_ID       optional; prepends a mention so the phone pushes
#   NOTIFY_MIN_SECONDS    optional; gate threshold in seconds, default 300
#
# Always exits 0. A broken webhook must never block Claude Code.

set -uo pipefail

STAMP="${CLAUDE_PROJECT_DIR:-.}/.claude/.turn-start"
THRESHOLD="${NOTIFY_MIN_SECONDS:-300}"

GATED=0
if [ "${1:-}" = "--gate" ]; then
    GATED=1
    shift
fi

MSG="${1:-CC event}"

# Drain stdin so the hook does not block on an unread pipe.
cat >/dev/null 2>&1 || true

[ -z "${DISCORD_WEBHOOK_URL:-}" ] && exit 0

if [ "$GATED" -eq 1 ]; then
    START=$(cat "$STAMP" 2>/dev/null || echo 0)
    case "$START" in
        ''|*[!0-9]*) START=0 ;;
    esac
    NOW=$(date +%s)
    ELAPSED=$(( NOW - START ))
    # START=0 means no timestamp was written; treat as a short turn and skip.
    if [ "$START" -eq 0 ] || [ "$ELAPSED" -lt "$THRESHOLD" ]; then
        exit 0
    fi
    MINS=$(( ELAPSED / 60 ))
    MSG="$MSG (${MINS}m)"
fi

if [ -n "${DISCORD_USER_ID:-}" ]; then
    CONTENT="<@${DISCORD_USER_ID}> ${MSG}"
else
    CONTENT="$MSG"
fi

# Build JSON without a here-doc so quoting stays predictable.
PAYLOAD=$(CONTENT="$CONTENT" python3 -c '
import json, os
print(json.dumps({"content": os.environ["CONTENT"]}))
' 2>/dev/null) || PAYLOAD="{\"content\":\"CC event\"}"

curl -s -m 5 \
    -H 'Content-Type: application/json' \
    -d "$PAYLOAD" \
    "$DISCORD_WEBHOOK_URL" >/dev/null 2>&1

exit 0
