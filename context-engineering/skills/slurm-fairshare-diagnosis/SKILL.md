---
name: slurm-fairshare-diagnosis
description: Diagnose SLURM Priority PENDING caused by account-level FairShare throttling. Use when sbatch job stays "PENDING (Priority)" for hours despite idle nodes, squeue shows no other user's jobs (PrivateData=jobs), or scontrol reports StartTime=Unknown. Triggers on "why is my job pending", "Priority forever", "StartTime Unknown", "job stuck in queue".
---

# SLURM FairShare Diagnosis

## When to Use

Your sbatch job stays `PENDING (Priority)` for much longer than expected, AND:
- `sinfo` shows plenty of idle nodes (57+, not a resource crunch)
- `squeue -u $USER` shows only your jobs (PrivateData=jobs hides others, misleading)
- Contiguity is not the issue (non-contiguous job also pends)
- `scontrol show job` reports `StartTime=Unknown`
- Intuition says "why am I stuck when nodes are free?"

The answer is almost always **account-level FairShare throttling** — other users' jobs have higher scheduling priority because you've used recently.

## Diagnosis Checklist

### 1. Confirm idle nodes exist

```bash
sinfo -t idle -h -o "%D"            # number of idle nodes
sinfo -o "%P %.6D %.10T %.12C %.8a" # partition × state breakdown
```

If this shows many idle nodes but your job doesn't start, resources aren't the problem.

### 2. Check your FairShare

```bash
sshare -u $(whoami) -o User,Account,RawShares,NormShares,RawUsage,FairShare
```

Key columns:
- `NormShares`: what fraction of cluster you're "entitled" to (based on admin allocation).
- `RawUsage`: seconds of compute charged to your account recently (half-life decay, typically 7-14 days).
- `FairShare`: computed priority weight. **< 0.01 = severely throttled**. Healthy is 0.3-0.7.

Example (throttled):
```
kangli.s5e brics.s5e   1   0.031250   725497344   0.003860
```
`FairShare=0.003860` means your priority is near the bottom of all users.

### 3. Check individual job Priority and StartTime

```bash
scontrol show job <JOBID> | grep -E "Priority|Reason|QOS|StartTime"
```

Interpret:
- `Priority=1` + `Reason=Priority` = bottom of queue, waiting behind higher-priority jobs.
- `StartTime=Unknown` = scheduler cannot predict; likely hours away. Often means the backfill window is full.

### 4. See where you rank

```bash
sprio -u $(whoami)                 # your job priorities
sprio -o "%.15i %.10u %.10Y %.10A %.10F"  # all jobs: id, user, age, fairshare, priority
```

## Recovery Options

### A. Wait it out (if no rush)

FairShare decays over time. At half-life ≈ 7 days, a heavy-usage account recovers to median in ~1-2 weeks of no submissions. Small, short jobs can backfill during this wait.

### B. Smaller / shorter jobs for backfill

Backfill scheduler fills gaps left by larger jobs. Jobs with:
- `--time < 30min`
- `--nodes=1`
- Lenient requirements (no --contiguous, no specific node list)

These are preferred by backfill. If you need urgent data, submit a 1-node short variant.

### C. Reduce resource footprint

- Drop `--contiguous` if `≥2 nodes` (prevents contiguity search narrowing candidate set)
- Drop `--exclusive` if job doesn't need whole node
- Request fewer GPUs (`--gres=gpu:1` vs `--gres=gpu:4`) for non-performance-critical runs

### D. Use a different QoS or account (if available)

```bash
sacctmgr show assoc format=User,Account,QOS where user=$(whoami)
```

Some clusters have a "devel" or "debug" QoS with higher priority but time limits. Submit with `--qos=devel`.

### E. Don't game the system

Do NOT submit dozens of redundant jobs hoping one gets scheduled faster — this further depletes your FairShare and makes the problem worse on the next sub window.

## Cluster-Specific Notes

**Isambard-AI (GH200)**:
- Partition `workq` is the default.
- `PrivateData=jobs` means `squeue -u other_user` returns empty; don't conclude queue is empty.
- `sinfo -t idle` is the authoritative free-nodes count.
- Half-life is ~7 days.

## Key Insight

**"Priority" reason + idle cluster = your account is the problem, not SLURM config**. No amount of resubmit / flag tuning will help; only time (waiting) or smaller jobs (for backfill).

## Related

- CLAUDE.md "Job submission rules" — covers sbatch etiquette (job-name, --contiguous, monitor checkpoints)
- `feedback_monitor_checkpoints.md` — 1/5/15/30min sacct exit check pattern
