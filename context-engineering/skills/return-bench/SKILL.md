---
user-invocable: true
description: Run return prediction benchmark — IC, Ranked IC, Direction Accuracy at multiple horizons. Trigger on "return bench", "IC bench", "direction accuracy".
arguments: "<infer_dir_or_run_name> [--horizons 10,50,100,250,500]"
---

# /return-bench — Return Prediction Benchmark

Measures whether generated LOB sequences predict real price direction.
Hedge-fund standard metrics: Pearson IC, Spearman Ranked IC, Direction Accuracy.

## Metrics

| Metric | Formula | What it measures |
|--------|---------|-----------------|
| IC (Pearson) | `corr(pred_log_return, real_log_return)` | Linear predictive power |
| Ranked IC (Spearman) | `rank_corr(pred_log_return, real_log_return)` | Monotonic predictive power |
| Direction Accuracy | `mean(sign(pred) == sign(real))` where `|real| > 1e-8` | Up/down classification |

## Setup

- **Conditioning**: 500 ticks (real data, given to model)
- **Generation**: 500 ticks (model output)
- **Horizons**: [10, 50, 100, 250, 500] ticks from conditioning end
- **Return**: `ln(mid_price[500+h] / mid_price[500])` (log return)
- **Mid-price**: `(best_ask + best_bid) / 2` from orderbook

## Behavior

1. **Resolve inference dir**:
   - If given a path, use directly
   - If given a run name, find in `~/AlphaTrade/lob_pipeline/inference_results/`

2. **Run benchmark**:
   ```bash
   PYTHON=/projects/s5e/quant/miniforge3/bin/python
   cd ~/AlphaTrade/lob_pipeline
   $PYTHON return_bench/run_return_bench.py \
       --infer_dir <path> \
       --horizons 10,50,100,250,500 \
       --workers 64 \
       --name <run_name>
   ```

3. **Report results** in table format:
   ```
   Horizon |    IC  | Rank IC | Dir Acc | N_total | N_eff | dt 25% | dt mean | dt med | dt 75%
   --------|--------|---------|---------|---------|-------|--------|---------|--------|-------
        10 |  0.xxx |   0.xxx |  xx.x%  |    3136 |  xxxx | x.xxs  |  x.xxs  | x.xxs  | x.xxs
   ```

## Rules

- Can run on login node (CPU only, no GPU needed)
- Uses existing inference results (data_gen/ + data_real/)
- Reads both .npy and .csv formats
- N_eff = samples after zero-filter (|real_return| > 1e-8)
- Time interval shows real wall-clock time for each horizon
