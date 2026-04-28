#!/bin/bash
# Claude Code status line script
# Displays full session chain (all ancestors) + git context
#
# Display format:
#   P:#1 <parent_uuid> -> P:#1.1 <mid_uuid> -> C:#1.1A <current_uuid> | date branch@commit | ctx N%
#   ^^ all ancestors marked P: (parent), last one marked C: (current)

CHAIN_FILE="${HOME}/.claude/session-chain.json"

# Read JSON input from stdin
input=$(cat)

# Extract basic info
ts=$(date '+%d%b %H:%M' | tr 'A-Z' 'a-z')
cwd=$(echo "$input" | jq -r '.cwd')
session_id=$(echo "$input" | jq -r '.session_id')
transcript_path=$(echo "$input" | jq -r '.transcript_path')

# Get git info
branch=$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')
commit=$(git -C "$cwd" rev-parse --short HEAD 2>/dev/null || echo '?')

# Derive task name from branch, cwd path, or current-task file
# Priority 1: branch name like exp/G1-scale-up -> "G1-scale-up"
# Priority 2: cwd path containing exp_G1-scale-up or tasks/G1-scale-up -> extract last segment
# Priority 3: .claude/current-task file (written by Claude at session start)
task_name=""
if [[ "$branch" =~ ^exp/(.+)$ ]]; then
    task_name="${BASH_REMATCH[1]}"
elif [[ "$cwd" =~ exp_([^/]+)(/|$) ]]; then
    task_name="${BASH_REMATCH[1]}"
elif [[ "$cwd" =~ /tasks/([^/]+)(/|$) ]]; then
    task_name="${BASH_REMATCH[1]}"
fi
# Fallback: read from current-task file if no task detected from branch/cwd
# Format: line 1 = task name, line 2 = task root path (project with tasks/ dir)
task_root=""
if [ -z "$task_name" ]; then
    task_file="${cwd}/.claude/current-task"
    if [ -f "$task_file" ]; then
        task_name=$(sed -n '1p' "$task_file" 2>/dev/null | tr -d '[:space:]')
        task_root=$(sed -n '2p' "$task_file" 2>/dev/null | tr -d '[:space:]')
    fi
fi
# Default task_root to cwd if not specified
if [ -z "$task_root" ]; then
    task_root="$cwd"
fi

# Build full session chain by walking parent links
# Result: "P:#1 <uuid> -> C:#1.1 <uuid>" (ancestors=P:, current=C:)
chain_display=""
if [ -f "$CHAIN_FILE" ]; then
    label=$(jq -r --arg sid "$session_id" '.[$sid].label // empty' "$CHAIN_FILE" 2>/dev/null)

    if [ -n "$label" ]; then
        # Walk up to collect all ancestors (current → parent → grandparent → ...)
        # Each entry includes creation timestamp from transcript birth time
        chain_parts=()
        transcript_dir=$(dirname "$transcript_path" 2>/dev/null)
        walk_id="$session_id"
        while [ -n "$walk_id" ] && [ "$walk_id" != "null" ]; do
            walk_label=$(jq -r --arg sid "$walk_id" '.[$sid].label // empty' "$CHAIN_FILE" 2>/dev/null)
            if [ -z "$walk_label" ]; then
                break
            fi
            # Get creation time from this session's transcript file
            walk_ts=""
            if [ -n "$transcript_dir" ]; then
                walk_file="${transcript_dir}/${walk_id}.jsonl"
                if [ -f "$walk_file" ]; then
                    walk_epoch=$(stat -c '%W' "$walk_file" 2>/dev/null)
                    if [ -n "$walk_epoch" ] && [ "$walk_epoch" != "0" ]; then
                        walk_ts=$(date -d "@${walk_epoch}" '+%d%b/%H:%M' 2>/dev/null | tr 'A-Z' 'a-z')
                    fi
                fi
            fi
            # Prepend (root first, current last) — UUID + timestamp only
            if [ -n "$walk_ts" ]; then
                chain_parts=("${walk_id} ${walk_ts}" "${chain_parts[@]}")
            else
                chain_parts=("${walk_id}" "${chain_parts[@]}")
            fi
            walk_id=$(jq -r --arg sid "$walk_id" '.[$sid].parent // empty' "$CHAIN_FILE" 2>/dev/null)
            if [ "$walk_id" = "null" ]; then
                break
            fi
        done

        # Build formatted entries with [N]: prefixes
        chain_entries=()
        for i in "${!chain_parts[@]}"; do
            seq_num=$((i + 1))
            chain_entries+=("[${seq_num}]:${chain_parts[$i]}")
        done

        # Build multi-line chain display (one entry per line)
        chain_display=""
        for i in "${!chain_entries[@]}"; do
            if [ "$i" -eq 0 ]; then
                chain_display="${chain_entries[$i]}"
            else
                chain_display="${chain_display}
${chain_entries[$i]}"
            fi
        done
    fi
fi

# Extract root session UUID from chain (chain_parts[0] = "#label uuid [ts]")
root_id=""
if [ ${#chain_parts[@]} -gt 0 ]; then
    # Second word is the UUID (first=#label, second=uuid, third=optional timestamp)
    root_id=$(echo "${chain_parts[0]}" | awk '{print $2}')
fi

# Get context window usage
tokens_info=""
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty' 2>/dev/null)
if [ -n "$used_pct" ]; then
    used_int=$(printf '%.0f' "$used_pct" 2>/dev/null || echo "$used_pct")
    tokens_info=" | ctx ${used_int}%"
fi

# Build task suffix
task_suffix=""
if [ -n "$task_name" ]; then
    task_suffix=" | task:${task_name}"
fi

# Get session init time from root session's transcript file birth time
# Uses root of the chain (not current fork) so init time stays fixed across forks
init_info=""
init_transcript="$transcript_path"
if [ -n "$root_id" ] && [ -n "$transcript_path" ]; then
    root_transcript="$(dirname "$transcript_path")/${root_id}.jsonl"
    if [ -f "$root_transcript" ]; then
        init_transcript="$root_transcript"
    fi
fi
if [ -n "$init_transcript" ] && [ -f "$init_transcript" ]; then
    birth_epoch=$(stat -c '%W' "$init_transcript" 2>/dev/null)
    if [ -n "$birth_epoch" ] && [ "$birth_epoch" != "0" ]; then
        init_date=$(date -d "@${birth_epoch}" '+%d%b' 2>/dev/null | tr 'A-Z' 'a-z')
        init_time=$(date -d "@${birth_epoch}" '+%H:%M' 2>/dev/null)
        init_info=" | init ${init_date} ${init_time}"
    fi
fi

# Count session chain depth: how many fork/resume cycles this conversation has been through
# s:5 = 5th session in the chain (#16 → #16.1 → #16.1A → #16.1A1 → #16.1A1b)
# Reuse chain_parts array which was already built by the chain walk above
chain_depth=${#chain_parts[@]}
chain_depth_info=""
if [ "$chain_depth" -gt 0 ]; then
    chain_depth_info=" | s:${chain_depth}"
fi

# Read all worktrees and join on single line
active_wt_file="${cwd}/.claude/active-worktrees"
for _d in "$cwd" "$(dirname "$cwd")" "$(dirname "$(dirname "$cwd")")"; do
    [ -f "${_d}/.claude/active-worktrees" ] && active_wt_file="${_d}/.claude/active-worktrees" && break
done
wt_suffix=""
if [ -f "$active_wt_file" ]; then
    wt_all=$(grep -v '^[[:space:]]*$' "$active_wt_file" 2>/dev/null | tr '\n' ' ' | sed 's/ $//')
    if [ -n "$wt_all" ]; then
        wt_suffix="  ${wt_all}"
    fi
fi

# Line 1: ctx% + task + most recent worktree (no branch, no init time)
# Strip leading " | " from tokens_info since branch@commit is removed
ctx_display="${tokens_info# | }"
printf '%s%s%s\n' "$ctx_display" "$task_suffix" "$wt_suffix"

# Line 3: claude.ai web link for this session
printf 'https://claude.ai/code/session_%s\n' "$session_id"

# Line 4: resume directory (strip /lus/lfs1aip2 prefix)
display_cwd="${cwd#/lus/lfs1aip2}"
printf 'cd %s\n' "$display_cwd"

# Line 5: resume command
printf 'claude --resume %s --fork-session\n' "$session_id"


# === Auto-write session chain to task's session-chain.md ===
_auto_record_session_chain() {
    # Guards: need task_name, cwd, and session not yet recorded
    [[ -z "$task_name" || -z "$cwd" || -z "$session_id" ]] && return
    local sentinel_dir="${HOME}/.claude/session-env/${session_id}"
    local sentinel="${sentinel_dir}/chain-recorded"
    [[ -f "$sentinel" ]] && return

    local chain_file_md="${task_root}/tasks/${task_name}/session-chain.md"
    mkdir -p "${task_root}/tasks/${task_name}" "$sentinel_dir"

    # Build P→C chain line from session-chain.json
    local my_label parent_id parent_label chain_line
    my_label=$(jq -r --arg id "$session_id" '.[$id].label // "?"' "$CHAIN_FILE" 2>/dev/null)
    parent_id=$(jq -r --arg id "$session_id" '.[$id].parent // empty' "$CHAIN_FILE" 2>/dev/null)

    if [[ -n "$parent_id" && "$parent_id" != "null" ]]; then
        parent_label=$(jq -r --arg id "$parent_id" '.[$id].label // "?"' "$CHAIN_FILE" 2>/dev/null)
        chain_line="P:#${parent_label} ${parent_id:0:8} -> C:#${my_label} ${session_id}"
    else
        chain_line="#${my_label} ${session_id}"
    fi

    local date_short
    date_short=$(date '+%d%b' | tr 'A-Z' 'a-z')

    # Append entry
    {
        echo ""
        echo "### $(date '+%Y-%m-%d %H:%M') #${my_label}"
        echo '```'
        echo "${chain_line} | ${date_short} ${branch}@${commit}"
        echo "cd ${cwd} && claude --resume ${session_id} --fork-session"
        echo "${transcript_path}"
        echo '```'
    } >> "$chain_file_md"

    touch "$sentinel"
}
_auto_record_session_chain 2>/dev/null
