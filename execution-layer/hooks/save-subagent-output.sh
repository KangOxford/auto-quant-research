#!/bin/bash
# SubagentStop hook: automatically save subagent output to markdown file
# Triggered when any subagent (Explore, Plan, general-purpose, etc.) completes
# Input: JSON on stdin with last_assistant_message, agent_type, agent_id, etc.

# Debug logging — always write to confirm hook fires
echo "$(date '+%Y%m%d_%H%M%S') SubagentStop hook fired" >> /tmp/subagent-hook-debug.log

INPUT=$(cat)

# Dump raw input for debugging
echo "$INPUT" | jq -r '.agent_type // "no-type"' >> /tmp/subagent-hook-debug.log

AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // "unknown"')
AGENT_ID=$(echo "$INPUT" | jq -r '.agent_id // "unknown"')
MESSAGE=$(echo "$INPUT" | jq -r '.last_assistant_message // ""')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.agent_transcript_path // ""')
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')

# Skip if no message content
if [ -z "$MESSAGE" ] || [ "$MESSAGE" = "null" ]; then
    exit 0
fi

# Output directory: <project>/.claude/subagent-outputs/
OUTDIR="${CWD}/.claude/subagent-outputs"
mkdir -p "${OUTDIR}"

# Short agent ID (first 8 chars) for filename readability
SHORT_ID=$(echo "$AGENT_ID" | cut -c1-8)
OUTFILE="${OUTDIR}/${TIMESTAMP}_${AGENT_TYPE}_${SHORT_ID}.md"

cat > "${OUTFILE}" << EOF
# Subagent Output: ${AGENT_TYPE}

| Field | Value |
|-------|-------|
| Agent Type | ${AGENT_TYPE} |
| Agent ID | ${AGENT_ID} |
| Timestamp | ${TIMESTAMP} |
| Transcript | ${TRANSCRIPT} |

## Response

${MESSAGE}
EOF

exit 0
