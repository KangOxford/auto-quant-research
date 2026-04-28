#!/bin/bash
# SessionStart hook: seeds iTerm2 tab title from latest customTitle in the
# session JSONL, then spawns a background watcher that keeps the tab in sync
# as /rename events append to the JSONL.

PY=/projects/s5e/quant/miniforge3/bin/python3
CD=/lus/lfs1aip2/projects/s5e/quant/.claude
WATCHER="$CD/bin/tab-title-watcher.py"

INPUT=$(cat)
SESSION_ID=$("$PY" -c "import sys,json; print(json.loads(sys.stdin.read()).get('session_id',''))" <<< "$INPUT" 2>/dev/null)
TRANSCRIPT=$("$PY" -c "import sys,json; print(json.loads(sys.stdin.read()).get('transcript_path',''))" <<< "$INPUT" 2>/dev/null)

TTY_PATH=$(tty 2>/dev/null)
[ -z "$TTY_PATH" ] || [ "$TTY_PATH" = "not a tty" ] && TTY_PATH=$(ps -o tty= -p $PPID 2>/dev/null | awk "{print \"/dev/\"\$1}")

[ -z "$TRANSCRIPT" ] && exit 0
[ ! -f "$TRANSCRIPT" ] && exit 0
[ -z "$TTY_PATH" ] && exit 0
[ ! -w "$TTY_PATH" ] && exit 0

# Kill any stale watcher for this session
PIDFILE="/tmp/tab-title-watcher.${SESSION_ID}.pid"
if [ -f "$PIDFILE" ]; then
    OLD=$(cat "$PIDFILE" 2>/dev/null)
    [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null && kill "$OLD" 2>/dev/null
    rm -f "$PIDFILE"
fi

# Spawn watcher; detach fully
nohup "$PY" "$WATCHER" "$TRANSCRIPT" "$TTY_PATH" > "/tmp/tab-title-watcher.${SESSION_ID}.log" 2>&1 < /dev/null &
echo $! > "$PIDFILE"
disown 2>/dev/null || true
exit 0
