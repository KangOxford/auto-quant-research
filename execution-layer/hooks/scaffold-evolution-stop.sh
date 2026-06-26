#!/usr/bin/env bash
# Stop hook: refresh scaffold-evolution packets when scaffold evidence changed.
#
# The hook is intentionally cheap and quiet:
# - exits unless this is a git repo with scaffold-evolution installed;
# - ignores generated reports so reports do not retrigger themselves;
# - hashes the relevant dirty surface to avoid rerunning on every Stop.

set -uo pipefail

INPUT=$(cat)
CWD=$(printf '%s' "$INPUT" | python3 -c 'import json, sys; print((json.load(sys.stdin).get("cwd") or "."))' 2>/dev/null)
[ -z "$CWD" ] && CWD="."

ROOT=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null) || exit 0
RUNNER="$ROOT/execution-layer/scaffold-evolution/run.py"
[ -f "$RUNNER" ] || exit 0

CHANGED_STATUS=$(
  git -C "$ROOT" status --porcelain -- \
    execution-layer/CLAUDE.md \
    execution-layer/PRINCIPLES.md \
    execution-layer/hooks \
    execution-layer/skills \
    execution-layer/scaffold-evolution/evaluate.py \
    execution-layer/scaffold-evolution/run.py \
    execution-layer/scaffold-evolution/suite-registry.json \
    execution-layer/scaffold-evolution/examples \
    execution-layer/scaffold-evolution/fixtures \
    execution-layer/scaffold-evolution/verifiers
)

CHANGED_PATHS=$(mktemp)
HASH_PAYLOAD=$(mktemp)
printf '%s\n' "$CHANGED_STATUS" |
  sed -E 's/^...//' |
  grep -v '^$' |
  grep -v '^execution-layer/scaffold-evolution/reports/' > "$CHANGED_PATHS"

[ -s "$CHANGED_PATHS" ] || {
  rm -f "$CHANGED_PATHS" "$HASH_PAYLOAD"
  exit 0
}

while IFS= read -r path; do
  printf '\n-- %s --\n' "$path" >> "$HASH_PAYLOAD"
  git -C "$ROOT" diff -- "$path" >> "$HASH_PAYLOAD" 2>/dev/null || true
  git -C "$ROOT" diff --cached -- "$path" >> "$HASH_PAYLOAD" 2>/dev/null || true
  if [ -f "$ROOT/$path" ]; then
    shasum -a 256 "$ROOT/$path" >> "$HASH_PAYLOAD" 2>/dev/null || true
  fi
done < "$CHANGED_PATHS"

HASH=$(shasum -a 256 "$HASH_PAYLOAD" | awk '{print $1}')
STATE="$ROOT/.git/scaffold-evolution-stop.hash"
if [ -f "$STATE" ] && [ "$(cat "$STATE" 2>/dev/null)" = "$HASH" ]; then
  rm -f "$CHANGED_PATHS" "$HASH_PAYLOAD"
  exit 0
fi

LOG_DIR="$ROOT/execution-layer/scaffold-evolution/reports"
mkdir -p "$LOG_DIR"
{
  echo "[$(date '+%F %T')] scaffold-evolution-stop: refreshing scenario-suite reports"
  python3 "$RUNNER" --changed-paths "$CHANGED_PATHS"
  echo "[$(date '+%F %T')] scaffold-evolution-stop: done"
} >> "$LOG_DIR/hook.log" 2>&1 || true
rm -f "$CHANGED_PATHS" "$HASH_PAYLOAD"

printf '%s' "$HASH" > "$STATE" 2>/dev/null || true
exit 0
