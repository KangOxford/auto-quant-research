---
name: find-wandb
description: Find wandb run URL, local wandb dir, and config for a SLURM job ID. Trigger on "find wandb", "wandb link", "wandb url", "wandb config for job".
user_invocable: true
---

# Find W&B Run by SLURM Job ID

Given a SLURM job ID, find the W&B run URL, local wandb directory, and full config.

## Method

### Step 1: Find the log file

```bash
JOBID=$1

# Search known experiment worktrees (fast, avoids lustre find)
for dir in /lus/lfs1aip2/projects/s5e/quant/AlphaTrade/experiments/exp_R1*; do
  for f in "$dir/logs_lobs5/training_${JOBID}_node0.log" "$dir/logs_lobs5/lobs5_${JOBID}.out"; do
    [ -f "$f" ] && echo "FOUND: $f" && LOGFILE="$f" && WORKTREE="$dir"
  done
done

# Fallback: main LOBS5 repo
if [ -z "$LOGFILE" ]; then
  for f in /lus/lfs1aip2/projects/s5e/quant/AlphaTrade/LOBS5/logs_lobs5/*${JOBID}*; do
    [ -f "$f" ] && echo "FOUND: $f" && LOGFILE="$f"
  done
fi
```

### Step 2: Extract wandb URL

```bash
grep -E "wandb.*View run|wandb.ai" "$LOGFILE" | tail -1
# Extract run ID from URL: .../runs/<RUN_ID>
```

### Step 3: Find local wandb directory

```bash
# wandb run dir naming: wandb/run-YYYYMMDD_HHMMSS-<RUN_ID>/
WANDB_DIR=$(find "$WORKTREE/wandb/" -maxdepth 1 -name "*${RUN_ID}*" -type d 2>/dev/null | head -1)
echo "Local wandb dir: $WANDB_DIR"
echo "Files: $WANDB_DIR/files/"
```

### Step 4: Extract config

Priority order (most reliable first):
1. **wandb-metadata.json** (has full CLI args): `$WANDB_DIR/files/wandb-metadata.json`
2. **Log file** argparse output: `grep "Namespace\|run_train.py" "$LOGFILE"`
3. **config.yaml** (if exists): `$WANDB_DIR/files/config.yaml`

**NEVER trust batch script defaults.** CLI args override everything.

## Output format

```
W&B URL:      https://wandb.ai/<entity>/<project>/runs/<run_id>
Local dir:    <full path to wandb/run-...-<run_id>/>
Metadata:     <full path>/files/wandb-metadata.json
Node0 log:    <full path to training_<JOBID>_node0.log>
SLURM log:    <full path to lobs5_<JOBID>.out>

Config:       (table of ALL parameters from wandb-metadata.json args)
```

## IMPORTANT

- **Never trust batch script defaults for job config.** CLI args override everything.
- Priority: wandb-metadata.json args > log file argparse > batch script defaults
- wandb-metadata.json `args` array is the COMPLETE command that was actually executed
- Environment variables (SSM_TYPE, MAMBA3_MIMO, etc.) may NOT appear in wandb-metadata; check log file for those
