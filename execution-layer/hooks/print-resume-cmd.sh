#!/bin/bash
# Stop hook: emit `claude --resume <session_id>` as a systemMessage so user can
# copy-paste the resume command from transcript without spending model tokens.
#
# Goal: insert resume line between the final assistant text and the
# "Cooked for Xs" footer (see user request 2026-04-14).
#
# Why systemMessage (and not /dev/tty): Ink TUI owns the screen; writing to tty
# races with Ink redraws (see feedback_no_tty_write_ink_tui memory).
# systemMessage is the schema-sanctioned transcript-level interface.
#
# Sync (no async: true) is required: async hook output is fire-and-forget and
# the runtime will not read JSON back from it.

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)

if [ -n "$SESSION_ID" ]; then
    jq -nc --arg msg "claude --resume ${SESSION_ID}" '{"systemMessage": $msg}'
fi
exit 0
