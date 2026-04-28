#!/bin/bash
# PostToolUse hook: auto-sync markdown files to Notion.
#
# Reads tool_input JSON from stdin, extracts file_path from Edit/Write/MultiEdit,
# then delegates to notion-sync-md.py. The python script checks
# ~/.claude/notion-sync-manifest.json to decide whether this file should sync.
#
# Zero Claude tokens — runs entirely in shell after tool completes.
# Errors logged to ~/.claude/notion-sync.log. Non-zero exit does not block
# Claude (PostToolUse is advisory).

set +e  # never block the caller on sync failure

INPUT=$(cat)
# Extract file_path (from tool_input) and session_id (top-level) in one shot.
# Output is exactly two lines: file_path on line 1, session_id on line 2.
PARSED=$(echo "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    tin = d.get("tool_input", {})
    print(tin.get("file_path", ""))
    print(d.get("session_id", ""))
except Exception:
    print("")
    print("")
' 2>/dev/null)
FILE_PATH=$(echo "$PARSED" | sed -n '1p')
SESSION_ID=$(echo "$PARSED" | sed -n '2p')

# Only process .md files (cheap filter to avoid python invocation on all writes)
case "$FILE_PATH" in
    *.md)
        python3 "${HOME}/.claude/hooks/notion-sync-md.py" "$FILE_PATH" "$SESSION_ID" &
        # Detach: don't wait (async). Hook should return fast.
        ;;
esac

exit 0
