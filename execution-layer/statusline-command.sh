#!/bin/bash
# Merged statusline: claude-hud (rich HUD) + auto-record
#
# Architecture:
#   stdin JSON → $input (captured once)
#   1. Pipe to claude-hud → rich display (model, context bar, tools, agents)
#   2. Pipe to statusline-session.sh (background, silent) → auto-record side effects
#
# Output (2 lines):
#   [Opus 4.6] LOBS5 │ shard-map *        ← claude-hud
#   Ctx ████████░░ 45% | 450K tok          ← claude-hud

input=$(cat)

# --- 1. claude-hud (rich ANSI-colored HUD) ---
plugin_dir=$(ls -d "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/claude-hud/claude-hud/*/ 2>/dev/null \
    | awk -F/ '{ print $(NF-1) "\t" $(0) }' | sort -t. -k1,1n -k2,2n -k3,3n -k4,4n | tail -1 | cut -f2-)
if [ -n "$plugin_dir" ]; then
    hud_output=$(echo "$input" | "/projects/s5e/quant/miniforge3/bin/node" "${plugin_dir}dist/index.js" 2>/dev/null)
    # CAVEAT (2026-04-12): account email display disabled per user request.
    # Reason: cluttered statusline with redundant info (email visible in terminal title already).
    # To restore: uncomment the account_email read and the printf line below.
    # account_email=$(cat "${HOME}/.claude/.account-email" 2>/dev/null)
    if [ -n "$hud_output" ]; then
        # Insert email + session label after first line of HUD output
        echo "$hud_output" | head -1
        # [ -n "$account_email" ] && printf '  %s\n' "$account_email"

        # Parse session id once (used by both global high-level and local stacks)
        _sid=$(echo "$input" | jq -r '.session_id // empty' 2>/dev/null)

        # GLOBAL per-session HIGH-LEVEL stack (rendered YELLOW, prefix "[global] ")
        # File: ~/.claude/session-cyan-labels/<sid>.txt
        #   (legacy dir name "session-cyan-labels" — content now YELLOW, color swapped 2026-04-12)
        # Semantic: "session-internal global" = high-level, slow-changing themes for THIS session.
        # Content rule: MUST describe content produced by THIS session, not cross-session catalogs.
        # Update: `echo "<theme>" >> $F && tail -5 $F > $F.tmp && mv $F.tmp $F`
        _global_label_file="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/session-cyan-labels/${_sid}.txt"
        if [ -n "$_sid" ] && [ -f "$_global_label_file" ]; then
            _global_labels=$(grep -v '^[[:space:]]*$' "$_global_label_file" | tail -5 | paste -sd '|' - | sed 's/|/ › /g')
            [ -n "$_global_labels" ] && printf '  \033[33m[global] %s\033[0m\n' "$_global_labels"
        fi

        # LOCAL per-session topic-shift stack (rendered CYAN, prefix "[local] ")
        # File: ~/.claude/session-labels/<sid>.txt (maintained by update-session-label.sh Stop hook)
        # Semantic: fast-changing topic-shift trail WITHIN this session.
        # Display: join last 5 non-empty lines with ' › ' separator on a single cyan line.
        _local_label_file="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/session-labels/${_sid}.txt"
        if [ -n "$_sid" ] && [ -f "$_local_label_file" ]; then
            _local_labels=$(grep -v '^[[:space:]]*$' "$_local_label_file" | tail -5 | paste -sd '|' - | sed 's/|/ › /g')
            [ -n "$_local_labels" ] && printf '  \033[36m[local] %s\033[0m\n' "$_local_labels"
        fi
        echo "$hud_output" | tail -n +2
    fi
fi

# --- 2. Side effects: run original session script for auto-record to session-chain.md ---
# Runs in background, stdout suppressed, only side effects matter
echo "$input" | bash "${HOME}/.claude/statusline-session.sh" >/dev/null 2>&1 &
