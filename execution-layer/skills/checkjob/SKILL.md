---
user-invocable: true
description: Show training job progress with standard progress bar format — triggered by "check", "watch", "status", "progress"
arguments: "[job_id] — optional SLURM job ID. If omitted, checks all running jobs for current user"
---

# /checkjob — Training Job Progress Bar

Display a standardized progress bar for running SLURM training jobs.

## Trigger

User says: `check`, `watch`, `status`, `progress`, or any variant.

## Behavior

### 1. Find running jobs

If no job ID given, find all running jobs:
```bash
squeue --me -o "%.10i %.20j %.8T %.10M %.6D %N" 2>/dev/null
```

### 2. For each job, extract data from logs

**Log locations** (check in order):
- `experiments/exp_*/logs_lobs5/training_{JOBID}_node0.log`
- `LOBS5/logs_lobs5/training_{JOBID}_node0.log`
- Find via: `find /lus/lfs1aip2/projects/s5e/quant/AlphaTrade -name "training_${JOBID}_node0.log" 2>/dev/null`

**Extract fields** (always use `grep -v "sol_gpu_cost_model"` to filter noise):

| Field | How to extract |
|-------|---------------|
| Step | `grep -oP '\d+/\d+' \| tail -1` from tqdm line |
| Loss | `grep '\[Timing\]' \| tail -1` → `loss=X.XXXX` |
| Speed | tqdm `X.XX s/it` or `X.XX it/s` |
| W&B URL | `grep "View run at" \| head -1` → full URL |
| steps_per_epoch | `grep "steps_per_epoch" \| tail -1` |
| Restore step | `grep "state.step" \| head -1` |
| Model config | `grep '\[NSA\]\|\[S5\]\|Trainable Parameters'` |
| Epoch | `grep '=>> Epoch\|Resuming from epoch'` |
| Log freshness | `$(( $(date +%s) - $(stat -c '%Y' "$LOGFILE") ))` seconds |

### 3. Output format

```
Job:   {JOBID} ({job_name})
Desc:  {auto_description}
Step:  {current}/{total}  [{progress_bar}]  {pct}%
Model: {arch} ({config}) | {params} params
Data:  {tickers} × {years} | test: {range}
Infra: {nodes}N / {gpus} GPU | BSZ={bsz}/gpu, gBSZ={gbsz}
Tokens/batch: {bsz_per_gpu × seq_len × n_gpus}
Loss:  {loss} (at step {n})
Speed: ~{speed} s/step ({it_per_s} it/s)
Time:  {elapsed} elapsed | {remaining} remaining | {limit} limit
ETA:   {estimate} — {can_finish_or_not}
W&B:   {full_wandb_url}
Ckpt:  {resume_info}
Log:   {full_log_path}
```

### 4. Description line (Desc)

Auto-generate a one-liner from job name + log context. Wrap at ~80 chars.

**Construction rules:**
1. Parse job name for keywords: tickers (8tk/GOOG), nodes (16n), model (mars/gdn/s5), time (4h/24h)
2. From log: extract architecture type (MarS/S5/GDN/NSA), encoding (24tok/5tok), optimizer, key flags
3. Combine into a human-readable sentence, e.g.:
   - `MarS LLaMA 399M, 8 tickers × 4yr, PyTorch DDP, chunked CE, first 16N multi-node run`
   - `S5 SSM 120M, GOOG 2022, shard-map hierarchical AllReduce, resume from step 135K`
   - `GDN 94M, 5-tok raw-price encoding, rope-ft, full epoch training`
4. If description exceeds 80 chars, word-wrap to next line with padding:
   ```
   Desc:  MarS LLaMA 399M, 8 tickers × 4yr, PyTorch DDP,
          chunked CE, first 16N multi-node run
   ```

### 5. Progress bar construction

- Total width: 30 characters
- Filled: `█` — count = `steps_done * 30 / steps_total`
- Empty: `░` — count = `30 - filled`
- Example: `[██████████████████████░░░░░░░░]  73.3%`

### 5. ETA calculation

```
steps_remaining = steps_per_epoch - (current_step - restore_step)
seconds_remaining = steps_remaining × speed_s_per_step
time_limit_seconds = parse from squeue %L
can_finish = seconds_remaining < time_limit_seconds
```

### 6. Log freshness check

If log hasn't been updated in >60 seconds at expected speed:
- Flag: `⚠️ Log stale ({N}s ago) — possible hang`
- Check `.err` file for OOM/NCCL errors

## Key Rules

- **W&B must be FULL URL** (e.g., `https://wandb.ai/oxford-lob/lob-nsa/runs/xxx`), never just run ID
- **Always filter** with `grep -v "sol_gpu_cost_model"` when reading logs
- **Use subagent** to read large log files — never dump raw logs into main context
- If multiple jobs running, show progress for ALL of them
- Execute immediately on trigger — don't ask questions

## Verification

The output matches the exact format above. All 11 required fields are present. W&B is a clickable full URL.
