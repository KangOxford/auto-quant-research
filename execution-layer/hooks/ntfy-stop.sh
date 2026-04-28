#!/bin/bash
# ntfy-stop.sh - Send phone notification when Claude Code stops
# Title = headline from Claude's last substantive response
# Body  = next few detail lines

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)

JSONL=$(ls ${HOME}/.claude/projects/*/${SESSION_ID}.jsonl 2>/dev/null | head -1)

TITLE="Claude Code"
BODY="Task completed - check session for details"

if [ -n "$JSONL" ] && [ -f "$JSONL" ]; then
    # Get last 3 assistant messages (skip API errors, login prompts etc.)
    RESPONSE=$(tac "$JSONL" | grep -m3 '"assistant"' | jq -r '
        .message.content
        | if type == "array"
          then [.[] | select(.type == "text") | .text] | join("\n")
          else .
          end' 2>/dev/null)

    if [ -n "$RESPONSE" ]; then
        # Filter noise: empty lines, table borders, code fences, API errors, insight blocks
        CLEAN=$(echo "$RESPONSE" | grep -Ev '^$|^\s*$|^---|^[┌├└│┐┘┬┴─]|^★|^`|^\|.*\|$|^API Error|^Please run')

        # Title: first substantive line, strip markdown
        T=$(echo "$CLEAN" | head -1 | sed 's/^#* //; s/\*\*//g; s/`//g' | cut -c1-60)

        # Body: lines 2-20, joined with newlines (maximize content)
        B=$(echo "$CLEAN" | sed -n '2,20p' | sed 's/^#* //; s/\*\*//g; s/`//g; s/^- //' | head -20 | cut -c1-120 | paste -sd$'\n')

        [ -n "$T" ] && TITLE="$T"
        # Body must have real content; if extraction got a title but no body, repeat title
        if [ -n "$B" ]; then
            BODY="$B"
        elif [ -n "$T" ]; then
            BODY="$T"
        fi
    fi
fi

curl -sf \
  -H "Title: ${TITLE}" \
  -H "Tags: white_check_mark" \
  -d "${BODY}" \
  ntfy.sh/kang-oxford-claude-code-19980301 2>/dev/null || true
