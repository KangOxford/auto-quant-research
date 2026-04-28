---
name: stale-worktree-triage
description: Detect stale git worktrees (>1 week behind mainline) and choose the right recovery path before sbatch. Prevents the "patch env, still fails" debug loop.
version: 1.0.0
allowed-tools: Bash, Read, Grep
alwaysApply: false
---

# Stale Worktree Triage

## When to Use

Trigger on ANY of these symptoms when submitting sbatch from an experiment worktree (e.g., `exp_R*`, `exp_G*`):

- Job crashes at JAX init with `_check_cuda_versions(raise_on_first_error=True)` or `xla_cuda12.initialize` errors
- Job crashes with `unrecognized arguments: --xxx` (new CLI args not in older `run_train.py`)
- Job OOMs at suspiciously large allocation (100+ GB) that same config works on mainline
- Worktree creation date is >7 days before current active main branch commits
- You're about to "fix" a worktree's env by copying files from mainline

**Counter-trigger (skip this skill)**: worktree is <3 days old OR actively developed (last commit <48h).

## Process

### Step 1: Age check (1 command)

```bash
WT=$1  # e.g. exp_R100_Mamba3_cudaffi
MAIN=exp/R1-Mamba3  # or whatever the active branch is
cd ~/AlphaTrade/experiments/$WT

# Days since worktree's HEAD
HEAD_AGE=$(($(date +%s) - $(git log -1 --format=%ct HEAD)))
HEAD_DAYS=$((HEAD_AGE / 86400))

# Days since mainline diverged from worktree  
DIVERGE=$(git log --oneline $MAIN ^HEAD 2>/dev/null | wc -l)

echo "Worktree HEAD age: $HEAD_DAYS days"
echo "Commits on $MAIN not in worktree: $DIVERGE"
```

### Step 2: Decision matrix

| HEAD age | Commits behind | Action |
|----------|----------------|--------|
| <3 days  | <20            | Safe to patch env only (copy node_wrapper.sh) |
| 3-7 days | 20-100         | Sync env + batch, spot-check run_train.py CLI |
| >7 days  | >100           | **ABANDON — sbatch from mainline, not this worktree** |
| >14 days | >500           | Worktree is archaeological. Don't try to revive. |

### Step 3: The "abandon" path

When abandon is the right call:

1. **Don't patch the stale worktree** — you'll hit cascading bugs:
   - `node_wrapper.sh` (env paths) — easy to fix
   - `train_full_autoreg.batch` (CLI args) — new args won't work with old `run_train.py`
   - `lob/train_helpers.py` (sharding/kernel logic) — silent bugs, manifest as OOM
   - Any of the above can hide the others, each fix reveals the next

2. **Submit from mainline instead**:
   ```bash
   cd ~/AlphaTrade/experiments/<mainline_worktree>
   # Handle any uncommitted changes first (commit, stash, or ask user)
   git status --short
   ```

3. **For uncommitted changes blocking sbatch**: ask user — options are (a) commit WIP, (b) stash, (c) new worktree, (d) abandon baseline. The CLAUDE.md rule "never sbatch uncommitted code" is non-negotiable and enforced by the permission system.

## Key Insights

### Why "patch env only" fails on >1 week stale worktrees

Worktrees accumulate bugs in 4 places:

```
Environment     →  node_wrapper.sh, LD_LIBRARY_PATH, NCCL paths
  ↓
Launch layer    →  train_full_autoreg.batch (sbatch args, env exports)
  ↓
Entry point    →  run_train.py (argparse, CLI)
  ↓
Training loop   →  train_helpers.py, sharding_utils.py (logic bugs)
```

A "partial sync" of only the top layer leaves the stale layers below. Each subsequent sbatch reveals the next layer's incompatibility. Observed pattern from 2026-04-20 session: 4 failed sbatches, each one peeling back the next layer:
1. Env CUDA paths stale → xla_cuda12 init error (misread as CUDA version)
2. Sync node_wrapper + batch → CLI args unrecognized
3. Revert batch only (keep node_wrapper) → OOM 197GB (train_helpers bug)
4. Give up on worktree, go to mainline → works

### Why distributed OOM errors LIE

When a multi-node job crashes:
- `node0` log often shows `xla_cuda12.initialize` failed OR "Shutdown barrier timeout"
- **These are symptoms**. The real cause is on another node that OOMed first, then GRPC cascade caused node0's JAX init to fail retroactively.
- `submit-job` skill's "scan ALL node logs" pattern catches this — ALWAYS grep all nodes for `RESOURCE_EXHAUSTED` before concluding root cause from node0 alone.

### Worktree creation cost vs salvage cost

Creating a fresh worktree from `<mainline>@HEAD`:
- Cost: 5 minutes (git worktree add + chmod + one commit for env)
- Benefit: clean git history, no stale code

Trying to salvage a stale worktree:
- Cost: unbounded (sub-bug hydra)
- Benefit: only if you need the specific uncommitted work in that worktree

**Heuristic**: Salvage ONLY if the worktree has UNIQUE uncommitted work you need. Otherwise create fresh.

## Verification

After making the abandon decision and submitting from mainline:

1. Check the new job reaches step 1+ of training (not JAX init)
2. Confirm `tqdm` shows nonzero steps in node0 log
3. Verify speed is within expected ballpark (compare to prior mainline runs)

If still failing after switching to mainline, the bug is in the config (not stale worktree) — switch to `multi-node-jax-ffi-debug` or `systematic-debugging` skill.

## Related Skills

- `submit-job`: how to sbatch (uses this skill's output to pick the right worktree)
- `multi-node-jax-ffi-debug`: deeper FFI-specific triage (after stale issue ruled out)
- `fix-git-lustre-io`: unrelated, for Lustre-specific git slowness

## History

- **2026-04-20** (v1): extracted from mamba3_siso_kernel_fusion_v2 session. R100 worktree (9 days stale) was one factor but **not the primary cause** of observed OOM.

- **2026-04-20** (v1.1 CORRECTION): The OOM pattern observed in 4 failed jobs (including from R1 mainline!) had a **different root cause**: env var `SSM_TYPE=${SSM_TYPE:-gdn}` defaulted to GDN (with Triton kernels, 10× memory blowup), not Mamba3 pure JAX as intended. The error was "wrong model, not stale worktree." Stale worktree is still a real pattern but I diagnosed prematurely.

  **New lesson (more valuable than the original)**: **Read config echoes first, error traces second.** The training log prints `[*] Trainable Parameters: 94058701` and `[GDN] num_heads=8...` BEFORE the crash. These lines answered "what model am I running?" in 2 seconds, whereas I spent 30+ minutes investigating OOM traces. Stack traces tell you WHERE it broke; config echoes tell you WHAT you ran. Check the latter first.

  **Debugging priority rule** (2026-04-20):
  ```
  1. Config echo (first ~50 lines of log) → what you *actually* ran
  2. Error trace (last ~30 lines of log)  → where it broke
  3. Diff against last working run        → what changed
  ```
  Never skip step 1. "Trainable Parameters" ≠ expected value = config bug, not code bug.
