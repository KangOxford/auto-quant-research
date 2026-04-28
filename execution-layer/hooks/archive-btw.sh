#!/usr/bin/env bash
# SubagentStop hook: archive /btw (aside_question subagent) Q+A
# into <cwd>/btw_log.md. Skips everything else.

set -o pipefail
LOG=/tmp/btw-archive-debug.log
echo "$(date '+%Y-%m-%d %H:%M:%S') SubagentStop fired" >> "$LOG"

INPUT=$(cat)
AGENT_TYPE=$(echo "$INPUT"   | jq -r '.agent_type // ""')
AGENT_ID=$(echo "$INPUT"     | jq -r '.agent_id // ""')
MESSAGE=$(echo "$INPUT"      | jq -r '.last_assistant_message // ""')
TRANSCRIPT=$(echo "$INPUT"   | jq -r '.agent_transcript_path // ""')
SESSION_ID=$(echo "$INPUT"   | jq -r '.session_id // ""')
PARENT_TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // ""')
CWD=$(echo "$INPUT"          | jq -r '.cwd // "."')

echo "  agent_type=$AGENT_TYPE cwd=$CWD" >> "$LOG"

# Only archive aside_question (the /btw handler)
if [ "$AGENT_TYPE" != "aside_question" ]; then
    exit 0
fi
# Nothing to archive if empty response
if [ -z "$MESSAGE" ] || [ "$MESSAGE" = "null" ]; then
    exit 0
fi

# Extract the original question from the subagent's JSONL
# (hook payload does NOT include the initial user prompt — only the last
# assistant message — so we read the first user turn out of the transcript)
QUESTION=$(python3 - "$TRANSCRIPT" <<'PY'
import json, sys
path = sys.argv[1]
try:
    fh = open(path)
except Exception:
    sys.exit(0)
for line in fh:
    try:
        d = json.loads(line)
    except Exception:
        continue
    if d.get("type") != "user":
        continue
    m = d.get("message") or {}
    if m.get("role") != "user":
        continue
    c = m.get("content")
    if isinstance(c, str):
        print(c.strip())
        break
    if isinstance(c, list):
        parts = []
        for b in c:
            if isinstance(b, dict) and b.get("type") == "text":
                t = (b.get("text") or "").strip()
                if t:
                    parts.append(t)
        if parts:
            print("\n\n".join(parts))
            break
PY
)

OUTFILE="${CWD}/btw_log.md"
TS=$(date '+%Y-%m-%d %H:%M:%S %Z')

# First write: seed a header
if [ ! -f "$OUTFILE" ]; then
    cat > "$OUTFILE" <<'EOF'
# /btw archive

Auto-captured side-question sessions. Each entry is the original question
(as sent to the `aside_question` subagent) and its final answer.

EOF
fi

{
    echo ""
    echo "## ${TS}"
    echo ""
    echo "_source_: aside_question subagent (SubagentStop hook)"
    echo "_agent_id_: \`${AGENT_ID}\`"
    echo "_subagent_transcript_: \`${TRANSCRIPT}\`"
    if [ -n "$PARENT_TRANSCRIPT" ] && [ "$PARENT_TRANSCRIPT" != "null" ]; then
        echo "_parent_transcript_: \`${PARENT_TRANSCRIPT}\`"
    fi
    if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
        echo "_resume_: \`claude --resume ${SESSION_ID}\`"
    fi
    echo ""
    echo "**Q:**"
    echo ""
    if [ -n "$QUESTION" ]; then
        # prefix each line with blockquote marker
        printf '%s\n' "$QUESTION" | sed 's/^/> /'
    else
        echo "> _(question not recoverable from transcript)_"
    fi
    echo ""
    echo "**A:**"
    echo ""
    printf '%s\n' "$MESSAGE"
    echo ""
    echo "---"
} >> "$OUTFILE"

echo "  wrote to $OUTFILE" >> "$LOG"
exit 0
