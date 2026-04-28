#!/bin/bash
# SessionStart hook: print resume command to the user's terminal (banner area).
#
# Strategy:
#   1. hook process exits immediately (non-blocking)
#   2. background subshell sleeps to let Ink TUI finish splash + banner render
#   3. then writes to /dev/tty with cursor save/restore to minimize Ink redraw conflict
#
# WARNING: Ink TUI owns the terminal screen. If Ink triggers a redraw after our
# write (e.g. Remote Control state change, token counter update), the resume line
# MAY be erased or cause layout shifting. If you see broken TUI, remove the
# SessionStart hook from ~/.claude/settings.json.

input=$(cat)
session_id=$(echo "$input" | jq -r '.session_id // empty' 2>/dev/null)

if [ -n "$session_id" ]; then
    (
        # Wait for Ink splash + remote-control banner + prompt render to stabilize.
        # 1.0s is empirical — too short races with Ink init, too long user already typing.
        sleep 1.0

        # ANSI escape sequence:
        #   \033[s   = save current cursor position (DECSC)
        #   \n       = newline (cursor moves down one line)
        #   \033[2m  = dim style on
        #   ...text...
        #   \033[0m  = all styles reset
        #   \033[u   = restore saved cursor position (DECRC)
        # Goal: write a line below current cursor, then return cursor so Ink's
        # internal cursor tracking stays consistent.
        { printf '\033[s\n  \033[2mclaude --resume %s\033[0m\033[u' "$session_id" > /dev/tty; } 2>/dev/null
    ) &
    disown
fi
exit 0
