#!/bin/bash
# PostToolUse wrapper for log-sbatch-to-sheets.py
# Reads JSON from stdin, fast-filters for sbatch, then runs Python to log to Google Sheets.

set -e

# Buffer stdin once
INPUT=$(cat)

# Fast filter: skip if not Bash with sbatch
if ! echo "$INPUT" | /projects/s5e/quant/miniforge3/bin/python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if d.get('tool_name') != 'Bash':
    sys.exit(1)
if 'sbatch' not in (d.get('tool_input', {}) or {}).get('command', '').lower():
    sys.exit(1)
sys.exit(0)
"; then
    exit 0
fi

# Run the Python logger (silent on success, errors logged to /tmp/log-sbatch-hook.err)
echo "$INPUT" | /projects/s5e/quant/miniforge3/bin/python3 \
    /lus/lfs1aip2/projects/s5e/quant/.claude/hooks/log-sbatch-to-sheets.py \
    >/dev/null 2>>/tmp/log-sbatch-hook.err || true

exit 0
