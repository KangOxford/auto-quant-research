#!/bin/bash
# Stop hook: sentinel-driven session label system.
#
# Maintains TWO per-session stacks from sentinels at the end of Claude responses:
#   - LOCAL  (~/.claude/session-labels/<sid>.txt):
#       <!-- label: X --> → append + tail -5 (rolling topic-shift trail, cyan)
#   - GLOBAL (~/.claude/session-cyan-labels/<sid>.txt):
#       <!-- global-labels: A | B | C | D | E --> → overwrite with 5-slot semantic
#       snapshot (yellow). Overwrite only if exactly 5 valid labels parsed.
#
# Extraction: tail -n 2000 transcript | grep -oE '<!-- ... -->' | tail -1
# HTML-comment sentinel format is invisible in rendered markdown but plain text
# in JSONL (grep matches directly).

input=$(cat)
session_id=$(echo "$input" | jq -r '.session_id // empty' 2>/dev/null)
transcript_path=$(echo "$input" | jq -r '.transcript_path // empty' 2>/dev/null)

[ -z "$session_id" ] && exit 0

LABEL_DIR="${HOME}/.claude/session-labels"
LABEL_FILE="${LABEL_DIR}/${session_id}.txt"
GLOBAL_DIR="${HOME}/.claude/session-cyan-labels"
GLOBAL_FILE="${GLOBAL_DIR}/${session_id}.txt"
mkdir -p "$LABEL_DIR" "$GLOBAL_DIR"

# ============================================================
# GLOBAL SENTINEL: overwrite if exactly 5 valid labels
# ============================================================
if [ -n "$transcript_path" ] && [ -f "$transcript_path" ]; then
    global_line=$(tail -n 2000 "$transcript_path" 2>/dev/null \
                  | grep -oE '<!-- global-labels: *[^>]+-->' \
                  | tail -1 \
                  | sed -E 's/<!-- global-labels: *(.*[^ ]) *-->/\1/')

    if [ -n "$global_line" ]; then
        IFS='|' read -ra parts <<< "$global_line"
        tmp=$(mktemp)
        count=0
        for p in "${parts[@]}"; do
            p="$(echo "$p" | sed -E 's/^ +| +$//g')"
            # Reject: empty, too short, contains template <>, all placeholder,
            # or starts with punctuation/symbol (must start with letter/digit/CJK)
            [ -z "$p" ] && continue
            [ ${#p} -lt 3 ] && continue
            [[ "$p" == *"<"* || "$p" == *">"* ]] && continue
            [[ "$p" =~ ^[X.[:space:]]+$ ]] && continue
            # First char must be alphanumeric or non-ASCII (≥0x80, e.g., CJK)
            first_byte=$(printf '%d' "'${p:0:1}")
            [ "$first_byte" -lt 128 ] && ! [[ "${p:0:1}" =~ [A-Za-z0-9] ]] && continue
            echo "$p" >> "$tmp"
            count=$((count+1))
        done
        # Overwrite only when exactly 5 valid labels parsed (protects existing file)
        if [ "$count" -eq 5 ]; then
            mv "$tmp" "$GLOBAL_FILE"
        else
            rm -f "$tmp"
        fi
    fi
fi

# ============================================================
# LOCAL SENTINEL: append + tail -5 (rolling topic-shift trail)
# ============================================================
sentinel=""
if [ -n "$transcript_path" ] && [ -f "$transcript_path" ]; then
    sentinel=$(tail -n 2000 "$transcript_path" 2>/dev/null \
               | grep -oE '<!-- label: *[^>]+-->' \
               | tail -1 \
               | sed -E 's/<!-- label: *(.*[^ ]) *-->/\1/')
fi

# Process local only if valid non-skip sentinel present.
# Validation (Unicode-aware): reject empty, too short, template chars, placeholder patterns,
# punctuation-leading strings (must start with letter/digit/CJK).
_first_byte=0
[ -n "$sentinel" ] && _first_byte=$(printf '%d' "'${sentinel:0:1}" 2>/dev/null)
_first_ok=0
[ "$_first_byte" -ge 128 ] && _first_ok=1
[[ "${sentinel:0:1}" =~ [A-Za-z0-9] ]] && _first_ok=1
if [ -n "$sentinel" ] && [ "$sentinel" != "skip" ] \
   && [ ${#sentinel} -ge 3 ] \
   && [[ "$sentinel" != *"<"* && "$sentinel" != *">"* ]] \
   && [[ ! "$sentinel" =~ ^[X.[:space:]]+$ ]] \
   && [ "$_first_ok" -eq 1 ]; then
    current_top=""
    [ -f "$LABEL_FILE" ] && current_top=$(grep -v '^[[:space:]]*$' "$LABEL_FILE" | tail -1)

    # Push only if different from current top (dedupe consecutive identical pushes)
    if [ "$current_top" != "$sentinel" ]; then
        echo "$sentinel" >> "$LABEL_FILE"
        tail -5 "$LABEL_FILE" > "${LABEL_FILE}.tmp" && mv "${LABEL_FILE}.tmp" "$LABEL_FILE"
    fi
fi

exit 0
