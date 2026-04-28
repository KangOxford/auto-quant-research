#!/usr/bin/env bash
# Stop hook: archive Q/A to <cwd>/btw_log.md whenever the last user prompt
# contains "/btw" anywhere.
#
# Complements archive-btw.sh (SubagentStop) which only fires when /btw is
# invoked as a proper slash command that dispatches the aside_question
# subagent. When the user types "/btw" mid-prompt the main agent answers
# directly and no SubagentStop fires — that gap is what this hook closes.
#
# Dedup: per-session hash file in /tmp prevents archiving the same prompt
# twice (e.g., if Stop fires multiple times for the same turn).

set -uo pipefail
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

DEBUG_LOG="$HOME/.claude/hook-debug.log"
_dlog() { echo "$(date '+%F %T') btw-main-stop: $1" >> "$DEBUG_LOG" 2>/dev/null; }

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
TRANSCRIPT=$(echo "$INPUT"  | jq -r '.transcript_path // empty' 2>/dev/null)
CWD=$(echo "$INPUT"         | jq -r '.cwd // "."' 2>/dev/null)

[ -z "$SESSION_ID" ] && { _dlog "exit: no session_id"; exit 0; }
[ -z "$TRANSCRIPT" ] && { _dlog "exit: no transcript_path"; exit 0; }
[ ! -f "$TRANSCRIPT" ] && { _dlog "exit: transcript missing $TRANSCRIPT"; exit 0; }

HASH_FILE="/tmp/claude-btw-last-archived-${SESSION_ID}.hash"

# Extract last user prompt + the assistant text blocks that followed it.
# Returns a compact JSON blob {q, a} on stdout; empty output means skip.
RESULT=$(python3 - "$TRANSCRIPT" <<'PY'
import json, sys
path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
except Exception:
    sys.exit(0)

def extract_text_from_content(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for b in c:
            if isinstance(b, dict) and b.get("type") == "text":
                t = b.get("text") or ""
                if t.strip():
                    parts.append(t)
        return "\n\n".join(parts)
    return ""

# Walk from end backward, find the most recent user turn that CONTAINS "/btw".
# Skipping non-/btw turns is required because system-inserted messages like
# "[Request interrupted by user for tool use]" look identical to real prompts
# (no isMeta, no sourceToolUseID). The hash dedup downstream prevents
# re-archiving an old /btw prompt that was already saved.
last_user = None
last_user_idx = -1
for i in range(len(lines) - 1, -1, -1):
    try:
        d = json.loads(lines[i])
    except Exception:
        continue
    if d.get("type") != "user":
        continue
    m = d.get("message") or {}
    if m.get("role") != "user":
        continue
    # Skip synthetic user messages: skill injections, tool-generated pseudo-turns.
    if d.get("isMeta") is True:
        continue
    if d.get("sourceToolUseID"):
        continue
    c = m.get("content")
    # Skip if content is a list of tool_result blocks (not a human prompt)
    if isinstance(c, list) and any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in c
    ):
        continue
    text = extract_text_from_content(c)
    if not text or not text.strip():
        continue
    if "/btw" not in text:
        continue
    last_user = text.strip()
    last_user_idx = i
    break

if not last_user:
    sys.exit(0)

# Collect assistant text blocks that appear AFTER the last user turn
assistant_parts = []
for line in lines[last_user_idx + 1:]:
    try:
        d = json.loads(line)
    except Exception:
        continue
    if d.get("type") != "assistant":
        continue
    m = d.get("message") or {}
    c = m.get("content")
    t = extract_text_from_content(c)
    if t:
        assistant_parts.append(t)

answer = "\n\n".join(assistant_parts).strip()
if not answer:
    sys.exit(0)

print(json.dumps({"q": last_user, "a": answer}, ensure_ascii=False))
PY
)

[ -z "$RESULT" ] && { _dlog "exit: no /btw in last user prompt (or empty answer)"; exit 0; }

Q=$(printf '%s' "$RESULT" | jq -r '.q' 2>/dev/null)
A=$(printf '%s' "$RESULT" | jq -r '.a' 2>/dev/null)
[ -z "$Q" ] && exit 0
[ -z "$A" ] && exit 0

HASH=$(printf '%s' "$Q" | sha256sum | cut -d' ' -f1)
if [ -f "$HASH_FILE" ] && [ "$(cat "$HASH_FILE" 2>/dev/null)" = "$HASH" ]; then
    _dlog "exit: already archived (session=${SESSION_ID} hash=${HASH:0:8})"
    exit 0
fi

OUTFILE="${CWD}/btw_log.md"
TS=$(date '+%Y-%m-%d %H:%M:%S %Z')

if [ ! -f "$OUTFILE" ]; then
    cat > "$OUTFILE" <<'EOF'
# /btw archive

Auto-captured Q/A for prompts containing `/btw`.

Two hooks feed this file:
- `btw-main-stop.sh` (Stop)         — main-agent answers when /btw appears mid-prompt
- `archive-btw.sh`   (SubagentStop) — aside_question subagent when /btw is a slash command

EOF
fi

{
    echo ""
    echo "## ${TS}"
    echo ""
    echo "_source_: main agent (Stop hook) · session \`${SESSION_ID}\`"
    echo "_transcript_: \`${TRANSCRIPT}\`"
    echo "_resume_: \`claude --resume ${SESSION_ID}\`"
    echo ""
    echo "**Q:**"
    echo ""
    printf '%s\n' "$Q" | sed 's/^/> /'
    echo ""
    echo "**A:**"
    echo ""
    printf '%s\n' "$A"
    echo ""
    echo "---"
} >> "$OUTFILE"

echo "$HASH" > "$HASH_FILE"
_dlog "archived Q/A to ${OUTFILE} (hash=${HASH:0:8})"
exit 0
