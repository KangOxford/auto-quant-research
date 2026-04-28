#!/bin/bash
# check-complete.sh — Stop hook for planning-with-files skill
# Checks task_plan.md for incomplete phases and warns if any remain.
# Always exits 0 (non-blocking) so it never prevents Claude from stopping.

PLAN_FILE="task_plan.md"

if [ ! -f "$PLAN_FILE" ]; then
    exit 0
fi

# Count incomplete items: lines with "- [ ]"
INCOMPLETE=$(grep -c "\- \[ \]" "$PLAN_FILE" 2>/dev/null || echo 0)
IN_PROGRESS=$(grep -c "in_progress" "$PLAN_FILE" 2>/dev/null || echo 0)

if [ "$INCOMPLETE" -gt 0 ] || [ "$IN_PROGRESS" -gt 0 ]; then
    echo ""
    echo "[planning-with-files] ⚠️  Task not fully complete:"
    echo "  Incomplete items: $INCOMPLETE"
    echo "  Phases in progress: $IN_PROGRESS"
    echo "  Review task_plan.md before closing session."
    echo ""
fi

exit 0
