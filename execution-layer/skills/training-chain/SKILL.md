---
name: training-chain
description: Use when user asks to show training chain, resume chain, job chain, task chain, job history, or progression across multiple SLURM job IDs — renders a vertical ASCII chain from root smoke test to current running job, with step numbers, W&B slugs, exit states, and transition reasons (auto-resume, SIGTERM, scale-up).
---

# Training Chain Visualizer

## Overview

Long trainings on this HPC setup are a **chain of SLURM jobs linked by `train_full_autoreg.batch`'s auto-resume logic**. When a job hits walltime or is SIGTERM'd, the batch script's tail saves a mid-epoch checkpoint and submits a follow-on job with `RESTORE_PATH=<prev_ckpt>`. This can cascade 5-10 deep before a full epoch completes.

When user asks about "the chain" they want to see the **whole ancestry**, not just the current running job.

## When to Use

**Trigger phrases (all mean "show me the chain"):**
- "training chain", "resume chain", "job chain", "task chain"
- "show me the list", "show the chain", "full chain"
- "all the jobs", "job history", "what's the ancestry"
- User pastes a `mamba3-*-resume` or `*-resume*` job name and asks "check"

**Don't use for:**
- Single-job status check → use `checkjob` skill instead
- Finding a specific W&B link → use `find-wandb` skill
- Full experiment report → use `checkstate` skill

## Output Format (MANDATORY)

```
Training Resume Chain (from the start)

j<ROOT> ──── <role> (<status>, step <N>, W&B <slug_or_blank>)
              │
              ▼ <transition_reason>
j<NEXT> ──── <role> (<status>, step <N>, W&B <slug>)
              │ auto-resume
              ▼
j<NEXT2> ──── <status> <duration>, step <N> (W&B <slug>) ← <optional annotation>
              │ auto-resume
              ▼
...
★ <CURRENT> ── RUNNING now, at step ~<N> (W&B <slug>, <time_left> left)
```

**Rules:**
- One line per SLURM job, chronologically top-to-bottom (root = oldest)
- Left: `j<JOBID> ──── ` (4 em-dashes) followed by one-line description
- Connector between jobs: `│` on a continued line, then `▼ <reason>` arrow
- Transition reasons: `scale up`, `auto-resume`, `manual restart`, `env blip`, `preempted`
- Highlight markers (optional):
  - `★` prefix on current running job or star-worthy entries (bench target, first successful long run)
  - Right-side annotation `← ...` for callouts ("bench target", "new chapter, large step jump", "first NaN-free long run")
- **Section header note**: `Training Resume Chain (from the start)` — the parenthetical label in the output format header is kept bilingual for context; body text mixes English and technical terms as appropriate

**Status keywords (keep short):**
- `COMPLETED <elapsed>` — exit 0:0, ran to completion or walltime
- `SIGTERM, step <N>` — exit 143 or 15, checkpoint saved
- `FAILED <duration>` — exit 1:0 or 2:0, crashed early
- `RUNNING <time_elapsed>` — currently in squeue

## How to Build the Chain

### Step 1: Find the ancestry

Given a job ID `<CUR>`, walk backward through `RESTORE_PATH` annotations:

```bash
# Each job's SLURM out has "Restore from: <CKPT_PATH>"
# ckpt_path format is .../checkpoints/j<PREV>_<WANDB>_<PREV>
# so PREV = <PREV>

LOGDIR=/lus/lfs1aip2/projects/s5e/quant/AlphaTrade/experiments/<WORKTREE>/logs_lobs5
CUR=<given job id>
while true; do
  SLURMOUT="$LOGDIR/lobs5_${CUR}.out"
  [ -f "$SLURMOUT" ] || break
  PREV=$(grep -oE 'checkpoints/j[0-9]+' "$SLURMOUT" | head -1 | sed 's/.*j//')
  [ -z "$PREV" ] || [ "$PREV" = "$CUR" ] && break
  echo "$PREV → $CUR"
  CUR=$PREV
done
```

Alternative (faster for kangli.s5e): `ls <worktree>/checkpoints/ | grep 'j' | sort` gives all checkpoint dirs chronologically, which mirrors the chain.

### Step 2: Per-job extract

For each job ID in chain:

```bash
# state + elapsed
STATE=$(sacct -j $J --format=State -n 2>/dev/null | head -1 | xargs)
ELA=$(sacct -j $J --format=Elapsed -n 2>/dev/null | head -1 | xargs)
EXIT=$(sacct -j $J --format=ExitCode -n 2>/dev/null | head -1 | xargs)

# step reached (from node0 log tail or Restore line)
STEP=$(grep -oE 'state\.step = [0-9]+' "$LOGDIR/training_${J}_node0.log" 2>/dev/null | head -1 | awk '{print $NF}')

# wandb slug
SLUG=$(grep -oE 'wandb.ai/[^/]+/[^/]+/runs/[a-z0-9]+' "$LOGDIR/training_${J}_node0.log" 2>/dev/null | head -1 | awk -F/ '{print $NF}')
```

### Step 3: Render in the format

Write output exactly matching the template. Respect:
- Vertical spacing (blank line between jobs)
- Em-dash count (4 after job ID)
- Arrow position (left-indented under connector)
- Include root smoke test even if small (context for user)

## Quick Reference

| User says | Response |
|---|---|
| "show me the chain" | Full chain, root to current |
| "check <JOB_ID>" AND job has `-resume` suffix | Full chain + current job detailed status |
| "task chain" | Same as training chain (user's wording for same thing) |
| "how far has MIMO gotten" | Full chain with emphasis on current step |

## Common Mistakes

| Mistake | Fix |
|---|---|
| Showing only current job | Walk backward all the way to root |
| Mixing up state.step (global) and tqdm progress (within-epoch) | Always clarify: "step 173K within epoch, state.step ≈ 245K global" |
| Using different arrow chars | Stick to `│` + `▼`, no unicode variants |
| Ignoring failed intermediate jobs | Include them (show `FAILED 8min (env blip)`)—they're part of the history |
| Forgetting the current running job's "★" prefix | Current RUNNING gets ★ prefix |
| Putting W&B in a separate row | Keep it inline on job's row as `(W&B <slug>)` |

## Real-World Example

This skill was extracted from MIMO 79M training analysis session where the chain reached depth 7+. User's own wording was "task chain"—so include that trigger. User explicitly approved the format in conversation.

Reference (MIMO chain at extraction time):
```
j4094065 → j4105625 → j4114758 → j4131391 → j4135447 → j4136574 → j4153463 → j4186255 → j4237848
```
8 jobs, spanning smoke test to 9h resume at step 245K+, W&B runs `c2bgltha → 9s33zw9c → x0qkwld0 → ... → p25c96q9 → <current>`.
