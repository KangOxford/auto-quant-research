---
name: bench-mars
description: Use when evaluating a MarS (PyTorch LLaMA) order-level model checkpoint. Runs inference (GPU) → decode (BinConverter) → LOBbench scoring. Trigger on "bench mars", "evaluate mars", "mars benchmark".
---

# /bench-mars — MarS Order-Level Benchmark

Evaluate a MarS PyTorch checkpoint: autoregressive inference → BinConverter decode → LOBbench scoring.

Uses the pipeline at `/lus/lfs1aip2/projects/s5e/lob_pipeline/.worktrees/mars-bench/`.

## Behavior

1. **Resolve checkpoint**: Find the `.pt` file (auto-detect latest step)
2. **Show command** before running
3. **Submit** one SLURM job per ticker
4. **Report** job IDs and output paths

## Usage

```bash
cd /lus/lfs1aip2/projects/s5e/lob_pipeline/.worktrees/mars-bench

./mars_bench/run_mars_bench.sh <CKPT_PATH> [OPTIONS]
```

## Options

| User says | Flag |
|-----------|------|
| "just GOOG" | `--stocks "GOOG"` |
| "all 8 tickers" | `--stocks "GOOG AAPL NVDA AMZN META TSLA MSFT AMD"` |
| "512 sequences" | `--n_sequences 512` |
| "step 10000" | `--checkpoint_step 10000` |
| "temperature 0.8" | `--temperature 0.8` |
| "top-k 100" | `--top_k 100` |
| "name v1" | `--name v1` |
| "4 hours" | `--walltime 04:00:00` |

## Pipeline

```
Checkpoint (.pt) → Inference (GPU, autoregressive)
  → order_indices [N_seq, N_gen]
  → Decode (BinConverter.sample) → LOBSTER 14-col .npy
  → LOBbench scoring (21 unconditional metrics)
  → scores/*.pkl + plots/*.png
```

## Output

```
results_mars_<name>/
  <STOCK>/
    <STOCK>_gen_indices.npy    # Raw generated order indices
    <STOCK>_real_indices.npy   # Ground truth indices
    data_gen/<STOCK>.npy       # Decoded LOBSTER format
    data_real/<STOCK>.npy
  scores/scores_*.pkl          # LOBbench metrics
  plots/*.png
```

## Rules

- ALWAYS show full command before submitting
- ALWAYS confirm with user before submitting
- MarS checkpoints are at `exp_O4c_MarS_PyTorch/checkpoints/j{JOBID}/step_*.pt`
- Default: GOOG only, 1024 sequences, temperature=1.0, top_k=50
