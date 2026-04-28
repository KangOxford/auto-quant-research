---
name: reuse-checkpoint-for-ablation
description: Before submitting new training jobs for ablation/diversity comparison experiments, search existing checkpoints across all users' experiments that match the needed config. Saves node-hours by reusing existing work.
version: 1.0.0
allowed-tools: Bash, Read, Grep, Glob, Agent
alwaysApply: false
---

# Reuse Existing Checkpoints for Ablation Experiments

## When to Use

Trigger on:
- About to submit new training jobs for ablation comparison (real vs zero, with vs without feature, etc.)
- Comparing models trained on different data distributions (single-ticker vs multi-ticker, diversity studies)
- Verifying hypothesis about how one variable (data diversity, optimizer, architecture) affects another

**Do NOT trigger** for:
- Brand new architecture/optimizer combinations with no precedent
- When you're sure the exact config has never been trained

## Process

### Step 1: Document the target config precisely

Before searching, write down EXACTLY what you need:

```
Architecture: 8M Mamba3 SISO (d=256, L=6, d_state=128)
Optimizer: Muon (muon_lr=0.01, ssm_lr=2e-3, wd=0.005)
Data: GOOG-only (single ticker)
Date range: 2024-04 to 2025-12 OR 2022-01 to 2025-12
Encoding: 26tok
Target steps: ~30,430 (to match comparison baseline)
Book config: needed both real AND zero variants
```

### Step 2: Spawn an Explore agent with thorough scope

Use `subagent_type=Explore` with `model=sonnet` (simple search task, not planning).

Prompt template:
```
Search comprehensively for {ARCHITECTURE} training jobs matching:
  - {CRITICAL_CONFIG_1}
  - {CRITICAL_CONFIG_2}
  - ...

Search locations:
1. All experiment dirs: /lus/lfs1aip2/projects/s5e/quant/AlphaTrade/experiments/exp_*/
2. User home dirs for other team members
3. Checkpoint metadata files (_CHECKPOINT_METADATA, scaling_law_runs.md)
4. W&B configs and SLURM logs

For each found checkpoint, report:
- Full checkpoint dir path
- Job ID
- Training config
- Checkpoint steps available
- Whether it matches ALL required criteria
```

### Step 3: Verify matches by reading actual training logs

Checkpoint metadata (Orbax `_CHECKPOINT_METADATA`) does NOT contain training config. The actual config is in:

1. **SLURM log header** (`logs_*/lobs5_<JOBID>.out` first ~50 lines):
   ```bash
   grep -E "TICKERS=|TRAIN_DATE_RANGE=|BOOK_ABLATION=|d_model=|opt_config=" \
     /path/to/exp_*/logs_lobs5/lobs5_<JOBID>.out | head -20
   ```

2. **Training log** (`logs_*/training_<JOBID>_node0.log`):
   ```bash
   grep -E "Multi-ticker mode|steps_per_epoch|Mamba3.*d_state" \
     /path/to/exp_*/logs_lobs5/training_<JOBID>_node0.log | head
   ```

3. **W&B summary** (if exists):
   ```bash
   find /path/to/exp_*/wandb/run-*-<WANDB_ID>/files/ -name wandb-summary.json
   ```

### Step 4: Match on samples-seen, NOT epochs or wall time

When comparing models trained on different data pools:

- ❌ WRONG: "both completed 1 epoch" (different pool sizes = different samples seen)
- ❌ WRONG: "both trained for 4 hours" (different throughput)
- ✅ RIGHT: `steps × global_batch_size = samples_seen`

Match on **closest samples-seen**, or resume the shorter run to match.

Example:
```
Aramis multi-ticker: 30,430 steps × 160 gBSZ = 4.87M samples seen
Valentin single-ticker (zero): 12,890 steps × 160 = 2.06M samples seen
       → 42% data volume gap is a confound; disclose in paper
```

### Step 5: Compute delta ratio for hypothesis test

The key test statistic for "X reduces Y importance" claims:

```python
delta_single = metric(baseline_single) - metric(ablation_single)
delta_multi  = metric(baseline_multi)  - metric(ablation_multi)
ratio = delta_single / delta_multi  # how much more X matters without diversity
```

Thresholds:
- ratio > 10x: strong support for hypothesis
- ratio 3-10x: moderate support
- ratio 1-3x: weak (may be noise)
- ratio < 1: hypothesis refuted

## Key Insights

1. **Cross-user checkpoints are gold**: Team members often train overlapping configs for different experiments. Aramis's scaling-law runs, Valentin's data ablations, your own production runs all may contain checkpoints for someone else's ablation comparison.

2. **Never trust the checkpoint metadata alone**: `_CHECKPOINT_METADATA` is Orbax internal state only. Training config is in SLURM logs or W&B configs.

3. **The partial-epoch confound**: Most research-scale training only covers 5-50% of an epoch. When comparing across data pools, the "training progress" fraction differs wildly. Use `samples × gBSZ` as the canonical measure.

4. **Env vars = ground truth**: Training config is set via env vars (TICKERS, TRAIN_DATE_RANGE, BOOK_ABLATION). If not in env, check `run_train.py` argparse defaults. Example: `BOOK_ABLATION` default is `"real"`.

5. **Search can be broad with Explore agent + narrow with grep**: First use Explore agent for exhaustive search, then use grep directly to verify specific candidates.

## Verification

Before claiming "no matching checkpoint exists", verify you searched:
- [ ] All `experiments/exp_*/checkpoints/` directories
- [ ] Other users' home dirs (`/home/s5e/aramis.s5e/`, etc.)
- [ ] Both Aramis and Valentin's git worktrees
- [ ] The SLURM logs (not just checkpoint metadata)
- [ ] W&B offline run dirs

If all these searches returned nothing, then submit training. Otherwise, LOBbench the existing checkpoint.

## Example from LOBS5 session (2026-04-13)

Task: Verify Aramis's "multi-ticker training reduces book importance" hypothesis.
Naive approach: Train 2 new GOOG-only models (real + zero book) = 28 node-hours.
Better approach: Found Valentin's existing j3714208 (real) + j3737228 (zero) at matching architecture. Result: 0 training hours, 2 LOBbench jobs (2 node-hours total), hypothesis strongly supported (book delta 27x larger in single-ticker).

Savings: **28 → 2 node-hours, 14x efficiency gain**.
