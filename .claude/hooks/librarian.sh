#!/usr/bin/env bash
# .claude/hooks/librarian.sh
#
# Librarian mode hook. Enforces the CLAIM format on assistant messages when
# Claude opts into it by emitting `--- CLAIM ---` delimiters.
#
# CLAIM format:
#
#   --- CLAIM ---
#   <claim text in your own words>
#
#   SOURCE: [<label>](<url>)
#   > <verbatim quote>
#
# Each `--- CLAIM ---` opens a new block. Blocks end at the next `--- CLAIM ---`
# or end-of-message. Each block must contain at least one `SOURCE:` line with
# an http(s) URL, and at least one `> ` blockquote line.
#
# Behavior:
#   - Reads Stop event JSON from stdin.
#   - If stop_hook_active is true, exits 0 (avoid loops).
#   - If the message has no `--- CLAIM ---` markers, exits 0 (opt-in only).
#   - Otherwise validates every block; exit 2 with a corrective stderr on fail.

set -euo pipefail

INPUT="$(cat)"

# Loop guard: don't block twice on the same turn.
STOP_ACTIVE=$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null || echo "false")
if [[ "$STOP_ACTIVE" == "true" ]]; then
    exit 0
fi

# Extract the last assistant message.
MSG=$(printf '%s' "$INPUT" | jq -r '.last_assistant_message // ""' 2>/dev/null || echo "")

# Opt-in: no CLAIM markers means librarian mode isn't engaged this turn.
if ! printf '%s\n' "$MSG" | grep -q '^--- CLAIM ---$'; then
    exit 0
fi

# Validate every CLAIM block.
CHECK_RESULT=$(printf '%s\n' "$MSG" | awk '
BEGIN {
    in_block = 0
    block_num = 0
    has_source = 0
    has_quote = 0
    fail = 0
    fail_msg = ""
}
function close_block() {
    if (in_block) {
        if (!has_source || !has_quote) {
            fail = 1
            fail_msg = fail_msg sprintf("  Block %d: ", block_num)
            if (!has_source) fail_msg = fail_msg "missing SOURCE: line with URL. "
            if (!has_quote)  fail_msg = fail_msg "missing > blockquote. "
            fail_msg = fail_msg "\n"
        }
    }
}
/^--- CLAIM ---$/ {
    close_block()
    block_num++
    in_block = 1
    has_source = 0
    has_quote = 0
    next
}
in_block && /^SOURCE:.*https?:\/\// { has_source = 1 }
in_block && /^> /                    { has_quote = 1 }
END {
    close_block()
    if (fail) {
        printf "FAIL\n%s", fail_msg
    } else {
        print "OK"
    }
}
')

STATUS=$(printf '%s\n' "$CHECK_RESULT" | head -n1)

if [[ "$STATUS" == "FAIL" ]]; then
    DETAILS=$(printf '%s\n' "$CHECK_RESULT" | tail -n +2)
    cat >&2 <<EOF
Librarian mode: CLAIM block(s) malformed.

Each CLAIM block must contain:
  - a SOURCE: line with an http(s) URL: SOURCE: [label](https://...)
  - a > blockquote line with a verbatim quote from that source

Details:
${DETAILS}
Fix the format and continue. If a claim cannot be sourced, do not wrap it in a CLAIM block; state it in prose and mark it (unverified).
EOF
    exit 2
fi

exit 0
