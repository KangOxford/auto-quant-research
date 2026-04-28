---
name: return-bench-mars
user-invocable: true
description: Run MarS return prediction benchmark — IC, Ranked IC, Direction Accuracy from order_index price slots. Trigger on "return bench mars", "mars IC", "mars direction accuracy".
arguments: "<results_dir> [--horizons 10,50,100,250,500] [--ticker GOOG]"
---

# /return-bench-mars — MarS Return Prediction Benchmark

Measures whether MarS-generated order sequences predict real price direction.
Uses price_slot from decoded order_index as proxy for price movement.

## Metrics

| Metric | What it measures |
|--------|-----------------|
| IC (Pearson) | Linear correlation between predicted and real cumulative price drift |
| Ranked IC (Spearman) | Monotonic correlation (rank-based) |
| Direction Accuracy | `mean(sign(pred) == sign(real))` where `|real| > 1e-8` |

## How it works

```
order_index → decode → price_slot (0-31, center=16)
  → drift = price_slot - 16 (negative=down, positive=up)
  → cumulative_drift[h] = sum(drift[0:h]) = "return" at horizon h
```

## Usage

Run on login node (CPU only):
```bash
PYTHON=/projects/s5e/quant/miniforge3/bin/python
cd /lus/lfs1aip2/projects/s5e/lob_pipeline/.worktrees/mars-bench

$PYTHON mars_bench/return_bench.py \
    --gen_indices <results_dir>/GOOG/GOOG_gen_indices.npy \
    --real_indices <results_dir>/GOOG/GOOG_real_indices.npy \
    --horizons 10,50,100,250,500 \
    --output_dir <results_dir>/scores \
    --ticker GOOG
```

## Output

```
Horizon |    IC  | Rank IC | Dir Acc | N_total | N_eff | Gen |ret| | Real |ret|
--------|--------|---------|---------|---------|-------|-----------|----------
     10 |  0.xxx |   0.xxx |  xx.x%  |    1024 |  xxxx |     x.xx  |     x.xx
```

## Rules

- Can run on login node (no GPU needed)
- Reads `*_gen_indices.npy` and `*_real_indices.npy` from benchmark output
- Default horizons: 10, 50, 100, 250, 500 orders
