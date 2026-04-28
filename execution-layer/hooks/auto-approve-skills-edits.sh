#!/bin/bash
# auto-approve-skills-edits.sh
#
# Handles TWO events: PreToolUse + PermissionRequest.
# Auto-approves operations on ~/.claude/{skills,hooks}/:
#   - Edit/Write/MultiEdit by tool_input.file_path prefix
#   - Bash        by tool_input.command substring match
#
# Why two events: PreToolUse fires before permission-mode check (covers classifier auto-approve);
# PermissionRequest fires when a dialog is ABOUT to show (covers sensitive-file hard gate that
# PreToolUse allow cannot bypass). Both needed for full coverage.
#
# Rationale: user policy 2026-04-14 — skills/hooks are personal Claude tool configuration;
# interactive prompts are unwanted friction. Other paths fall through.

INPUT=$(cat)
EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // empty')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Debug log: one line per invocation so we can observe hook activity
DEBUG_LOG="$HOME/.claude/hook-debug.log"
echo "$(date '+%F %T') event=$EVENT tool=$TOOL_NAME path=${FILE_PATH:0:100} cmd=${COMMAND:0:100}" >> "$DEBUG_LOG" 2>/dev/null

SKILLS_DIR="$HOME/.claude/skills/"
HOOKS_DIR="$HOME/.claude/hooks/"
APPROVED=0

# Edit/Write/MultiEdit: file_path under target dirs, or exact CLAUDE.md
if [[ -n "$FILE_PATH" ]]; then
  if [[ "$FILE_PATH" == "$SKILLS_DIR"* || \
        "$FILE_PATH" == "$HOOKS_DIR"* || \
        "$FILE_PATH" == "$HOME/.claude/CLAUDE.md" ]]; then
    APPROVED=1
  fi
fi

# Bash: command references target dir path (absolute or ~/ form)
if [[ "$TOOL_NAME" == "Bash" && -n "$COMMAND" ]]; then
  if [[ "$COMMAND" == *"$SKILLS_DIR"* || \
        "$COMMAND" == *"$HOOKS_DIR"* || \
        "$COMMAND" == *"~/.claude/skills/"* || \
        "$COMMAND" == *"~/.claude/hooks/"* ]]; then
    APPROVED=1
  fi
fi

# MCP tools: auto-approve read-only operations (conservative whitelist of read verbs).
# Write ops (add_/create_/update_/delete_/log_/batch_) fall through to normal flow.
if [[ "$TOOL_NAME" == mcp__* ]]; then
  TN_LOWER="${TOOL_NAME,,}"
  if [[ "$TN_LOWER" == *_get_*    || "$TN_LOWER" == *_list_*    || \
        "$TN_LOWER" == *_query_*  || "$TN_LOWER" == *_search*   || \
        "$TN_LOWER" == *_find_*   || "$TN_LOWER" == *_read_*    || \
        "$TN_LOWER" == *_count_*  || "$TN_LOWER" == *_infer_*   || \
        "$TN_LOWER" == *_details* || "$TN_LOWER" == *_versions* || \
        "$TN_LOWER" == *_history* || "$TN_LOWER" == *_compare_* ]]; then
    APPROVED=1
  fi
fi

if [[ $APPROVED -eq 1 ]]; then
  if [[ "$EVENT" == "PreToolUse" ]]; then
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Auto-approved: ~/.claude/{skills,hooks}/ (user policy)"
  }
}
EOF
  elif [[ "$EVENT" == "PermissionRequest" ]]; then
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "allow"
    }
  }
}
EOF
  fi
fi

exit 0
