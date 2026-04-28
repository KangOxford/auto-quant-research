---
name: moveon
description: Restore background job monitors after session reconnect. Reads active_monitors.jsonl, checks which SLURM jobs are still running, re-launches monitors for active jobs, reports completed jobs. Trigger on "moveon", "move on", "reconnect", "restore monitors", "go on".
user-invocable: true
arguments: "[--clean] — optional flag to clear all monitors without re-launching"
allowed-tools: Bash, Read, Write, Glob, Grep
---

# /moveon — Session Reconnect & Monitor Restore

Seamlessly restore background SLURM job monitors after `claude --resume` reconnect.

## Architecture

```
                        ┌─────────────────────┐
                        │ active_monitors.jsonl│  (persistent state)
                        │  {job_id, name, log} │
                        └──────────┬───────────┘
                                   │
          ┌────────────────────────┼─────────────────────────┐
          │                        │                          │
    ┌─────▼──────┐          ┌─────▼──────┐           ┌──────▼──────┐
    │  squeue -j  │          │  squeue -j  │           │  squeue -j   │
    │  RUNNING    │          │  PENDING    │           │  NOT FOUND   │
    └─────┬──────┘          └─────┬──────┘           └──────┬──────┘
          │                       │                          │
   Re-launch monitor       Re-launch monitor          sacct + tail log
   (progressive C)         (wait-for-start)           → report final
          │                       │                          │
    Keep in JSONL           Keep in JSONL            Remove from JSONL
```

## Tracking File

**Path**: `<repo_root>/.claude/active_monitors.jsonl`

For this project: `/projects/s5e/quant/AlphaTrade/LOBS5/.claude/active_monitors.jsonl`

**Format** (one JSON object per line, appendable with `echo >>`):
```jsonl
{"job_id":"3388625","name":"dfm-gdn-16n-24h","log":"/lus/.../dfm_3388625_node0.log","slurm_log":"/lus/.../dfm_3388625.out","worktree":"/lus/.../exp_O12_GDN_DFM","ts":"2026-03-27T10:00:00Z","timeout_ms":86400000}
```

| Field | Required | Description |
|-------|----------|-------------|
| `job_id` | yes | SLURM job ID |
| `name` | yes | Job name (from `--job-name`) |
| `log` | yes | Primary log file path (node0 log or main .out) |
| `slurm_log` | no | SLURM .out file path |
| `worktree` | no | Worktree or experiment directory |
| `ts` | yes | Submission timestamp (UTC ISO 8601) |
| `timeout_ms` | no | Original monitor timeout in ms |

## Save Protocol (after every sbatch + monitor launch)

**This happens AUTOMATICALLY after every sbatch**, not during /moveon.

After launching a background monitor, append one line to the tracking file:

```bash
MONITORS_FILE="/projects/s5e/quant/AlphaTrade/LOBS5/.claude/active_monitors.jsonl"
echo '{"job_id":"'"${JOBID}"'","name":"'"${JOBNAME}"'","log":"'"${LOGFILE}"'","slurm_log":"'"${SLURM_LOG}"'","worktree":"'"${WORKTREE}"'","ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"}' >> "${MONITORS_FILE}"
```

**Rules**:
- Append-only during normal operation (only /moveon rewrites the file)
- One line per job, even if multiple monitors exist for the same job
- If the same job_id already exists in the file, it's fine (deduped during restore)

## Restore Protocol (/moveon invocation)

### Step 1: Read tracking file

```bash
MONITORS_FILE="/projects/s5e/quant/AlphaTrade/LOBS5/.claude/active_monitors.jsonl"
cat "${MONITORS_FILE}" 2>/dev/null || echo "NO_FILE"
```

If file doesn't exist or is empty: report "No active monitors tracked." and exit.

### Step 2: Deduplicate by job_id

If multiple entries have the same job_id, keep only the latest one (last line wins).

### Step 3: Check each job's status

For each unique job_id:

```bash
STATE=$(squeue -j ${JOBID} -h -o "%T" 2>/dev/null)
```

Classify into three buckets:

| State | Action |
|-------|--------|
| `RUNNING` | Re-launch progressive monitor (Schema C) |
| `PENDING` / `CONFIGURING` | Re-launch wait-then-monitor |
| empty / error (job gone) | Query `sacct`, read final log, report completion |

### Step 4: Re-launch monitors for active jobs

For **RUNNING** jobs, use the standard progressive monitor (Schema C from CLAUDE.md):

```bash
JOBID=<id>; LOGFILE=<log_path>
for CHECKPOINT in 60 300 900 1800; do
    sleep $CHECKPOINT
    STATE=$(squeue -j ${JOBID} -h -o "%T" 2>/dev/null || echo "DONE")
    MINS=$((CHECKPOINT / 60))
    if [ "$STATE" = "DONE" ] || [ -z "$STATE" ]; then
        EXIT=$(sacct -j ${JOBID} --format=ExitCode -n 2>/dev/null | head -1 | xargs)
        echo "=== ${MINS}min: DONE (exit ${EXIT}) ==="
        [ "$EXIT" != "0:0" ] && grep -iE "error|oom|assert" "$LOGFILE" 2>/dev/null \
            | grep -v "CUDA_ERROR_NO_DEVICE\|xla_cuda12" | tail -5
        break
    fi
    echo "=== ${MINS}min: ${STATE} ==="
    case $CHECKPOINT in
        60)   grep -iE "error|oom|fatal" "$LOGFILE" 2>/dev/null \
              | grep -v "CUDA_ERROR_NO_DEVICE\|xla_cuda12" | tail -3 ;;
        300)  grep -v "sol_gpu_cost_model" "$LOGFILE" 2>/dev/null \
              | grep -E "it/s|compile|Timing" | tail -3 ;;
        900)  grep -oP 'Epoch \d+/\d+:.*?loss=[\d.]+' "$LOGFILE" 2>/dev/null \
              | tail -1 ;;
        1800) grep '\[.*Timing\]' "$LOGFILE" 2>/dev/null | tail -3 ;;
    esac
done
```

Run each with `run_in_background=true`.

For **PENDING** jobs, launch a wait-then-monitor:

```bash
JOBID=<id>; LOGFILE=<log_path>
for i in $(seq 1 240); do
    STATE=$(squeue -j ${JOBID} -h -o "%T" 2>/dev/null || echo "GONE")
    if [ "$STATE" = "RUNNING" ]; then
        echo "=== Job ${JOBID} now RUNNING ==="
        for CHECKPOINT in 60 300 900 1800; do
            sleep $CHECKPOINT
            STATE2=$(squeue -j ${JOBID} -h -o "%T" 2>/dev/null || echo "DONE")
            MINS=$((CHECKPOINT / 60))
            if [ "$STATE2" = "DONE" ] || [ -z "$STATE2" ]; then
                EXIT=$(sacct -j ${JOBID} --format=ExitCode -n 2>/dev/null | head -1 | xargs)
                echo "=== ${MINS}min: DONE (exit ${EXIT}) ==="
                break 2
            fi
            echo "=== ${MINS}min: ${STATE2} ==="
        done
        break
    elif [ "$STATE" = "GONE" ] || [ -z "$STATE" ]; then
        echo "=== Job ${JOBID} disappeared (cancelled or failed before start) ==="
        break
    fi
    sleep 30
done
```

### Step 5: Report completed jobs

For jobs that already finished, use a **subagent** to read the log and extract:
- Exit code from `sacct`
- Last 20 lines of log (filtered)
- W&B URL if present
- Final loss/timing metrics

Print a summary:
```
Completed: Job 3388625 (dfm-gdn-16n-24h)
  State:   COMPLETED (exit 0:0)
  Elapsed: 18:42:15
  Last log: [Timing] Epoch 1 complete, loss=0.4532
  W&B: https://wandb.ai/...
```

### Step 6: Rewrite tracking file

Remove completed jobs, keep only active ones:

```bash
python3 -c "
import json, sys
active_ids = set(sys.argv[1:])
lines = open('${MONITORS_FILE}').readlines()
with open('${MONITORS_FILE}', 'w') as f:
    seen = set()
    for line in reversed(lines):
        obj = json.loads(line.strip())
        jid = obj['job_id']
        if jid in active_ids and jid not in seen:
            f.write(line if line.endswith('\n') else line + '\n')
            seen.add(jid)
" ${ACTIVE_JOB_IDS}
```

### Step 7: Print summary table

```
/moveon Summary
┌──────────┬────────────────────┬──────────┬─────────────────────────────────┐
│  Job ID  │     Job Name       │  Status  │   Action                        │
├──────────┼────────────────────┼──────────┼─────────────────────────────────┤
│ 3388625  │ dfm-gdn-16n-24h    │ RUNNING  │ Monitor re-launched             │
│ 3388618  │ dfm-gdn-4n-bench   │ COMPLETED│ Final: exit 0:0, loss 0.45     │
│ 3388565  │ dfm-gdn-2n-smoke   │ PENDING  │ Wait-monitor launched           │
└──────────┴────────────────────┴──────────┴─────────────────────────────────┘
Active monitors: 2 | Completed: 1 | Cleaned up: 1
```

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| No tracking file exists | Print "No active monitors." and exit |
| All jobs completed | Report all completions, delete tracking file |
| Job cancelled by user | Treat as completed, show CANCELLED state |
| Same job_id multiple times | Dedup: last entry wins |
| `--clean` flag | Remove all entries without re-launching anything |
| Tracking file has stale entries (days old) | Check anyway; sacct covers 7 days of history |

## Integration with /submit-job

The submit-job skill's Step 6 (Post-Submit Auto-Check) MUST also append to `active_monitors.jsonl` after launching the background monitor. This is the "save" side of the record-and-replay protocol.

**Add this after the background monitor `Bash` call in submit-job:**

```bash
MONITORS_FILE="/projects/s5e/quant/AlphaTrade/LOBS5/.claude/active_monitors.jsonl"
echo '{"job_id":"'"${JOBID}"'","name":"'"${JOBNAME}"'","log":"'"${LOGFILE}"'","ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"}' >> "${MONITORS_FILE}"
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Forgetting to save after sbatch | submit-job skill enforces it |
| Re-launching monitor for completed job | Always check squeue/sacct first |
| Tracking file grows unbounded | /moveon cleans up completed entries |
| Multiple monitors for same job | Dedup by job_id during restore |
