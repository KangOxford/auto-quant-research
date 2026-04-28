#!/usr/bin/env bash
# Stop hook: extract "★ Insight ─...─" blocks from last assistant turn.
# Appends to a local markdown log and a standalone Overleaf tex file,
# then async-pushes the tex change to Overleaf (if the repo is available).
#
# Input (stdin JSON from Claude Code Stop hook):
#   { "session_id": "...", "transcript_path": "...", "cwd": "..." }
#
# Side effects:
#   - append to ~/.claude/insights-log.md
#   - append to ~/AlphaTrade/LOBS5/overleaf/.../drafts/kang/insights.tex (if dir exists)
#   - git add/commit/push in background (best-effort; failures log to ~/.claude/insights-push-errors.log)
#
# Exit 0 on success or no-op. Never blocks the next turn.

set -uo pipefail

INPUT=$(cat)

# Export to env so Python script can read safely (avoid shell interpolation pitfalls)
export CC_TRANSCRIPT=$(printf '%s' "$INPUT" | jq -r '.transcript_path // ""')
export CC_SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // ""')
export CC_CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty')

[ -z "$CC_TRANSCRIPT" ] && exit 0
[ ! -f "$CC_TRANSCRIPT" ] && exit 0

exec python3 "$HOME/.claude/hooks/extract-insights.py"
