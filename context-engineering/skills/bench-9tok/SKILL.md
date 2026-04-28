---
user-invocable: true
description: Benchmark a 9tok GDN model checkpoint using standalone inference + LOBbench scoring. Trigger on "bench 9tok", "benchmark 9tok", "lob bench 9tok".
arguments: "<checkpoint_path> [options]"
---

# /bench-9tok — 9tok LOBbench Pipeline

Standalone LOBbench evaluation for P1 9-token GDN models: **inference (GPU, 4 parallel) → format conversion → LOBbench scoring**.

Does NOT use the standard `lob_pipeline/run_inference.py` (which has 24tok-only assumptions). Instead uses `bench_9tok_infer.py` + `bench_9tok.batch` in the P1 worktree.

## Behavior

1. **Resolve checkpoint**: verify path + step exist
2. **Show config table** before submitting:
   ```
   ┌──────────────┬────────────────────────────────┐
   │ Parameter    │ Value                          │
   ├──────────────┼────────────────────────────────┤
   │ Checkpoint   │ /path/to/ckpt                  │
   │ Step         │ 113775                         │
   │ Ticker       │ GOOG                           │
   │ Sequences    │ 1024                           │
   │ Cond / Gen   │ 500 / 500                      │
   │ Nodes / GPUs │ 1N / 4 GPU                     │
   │ Walltime     │ 24:00:00                       │
   │ Output       │ inference_results/...          │
   └──────────────┴────────────────────────────────┘
   ```
3. **Submit**: `sbatch --job-name=<name> bench_9tok.batch`
4. **Report** job ID + log path

## Defaults

| Parameter | Default | Override env var |
|-----------|---------|-----------------|
| Ticker | GOOG | `TICKER=AAPL` |
| Sequences | 1024 | `N_SEQ=512` |
| Cond msgs | 500 | `N_COND=500` |
| Gen msgs | 500 | `N_GEN=500` |
| Tick size | 100 | `TICK_SIZE=100` |
| Temperature | 1.0 | `TEMP=0.8` |
| Walltime | 24h | `--time=04:00:00` |
| Nodes | 1 | fixed |
| GPUs | 4 | fixed |

## Usage

```bash
# Default: GOOG, 1024 seq, step 113775
/bench-9tok checkpoints/j3255163_3f02wfri_3255163

# With options
/bench-9tok checkpoints/j3255163_3f02wfri_3255163 step 113775 GOOG 512 sequences

# Quick test (8 sequences, 30min)
/bench-9tok checkpoints/j3255163_3f02wfri_3255163 quick test
```

## Mapping

| User says | Action |
|-----------|--------|
| "quick test" / "test" | `N_SEQ=8 N_GEN=50 --time=00:30:00` |
| "GOOG" / "AAPL" / ticker | `TICKER=<ticker>` |
| "512 sequences" | `N_SEQ=512` |
| "step 80000" | `STEP=80000` |
| "temp 0.8" | `TEMP=0.8` |

## Command Template

```bash
cd /lus/lfs1aip2/projects/s5e/quant/AlphaTrade/experiments/exp_P1_sigma_order

CKPT=<path> STEP=<step> TICKER=<ticker> N_SEQ=<n> \
RUN_NAME="p1b-9tok-<name>" \
sbatch --job-name=bench-9tok-<ticker> --time=<walltime> bench_9tok.batch
```

## Output Structure

```
exp_P1_sigma_order/
  inference_results/<run_name>_<ticker>_<jobid>/
    data_real/    # ground-truth LOBSTER CSVs (with real order IDs + abs prices)
    data_gen/     # generated LOBSTER CSVs (synthetic OIDs, reconstructed abs prices)
    data_cond/    # conditioning LOBSTER CSVs
    bench_config_gpu*.json

lob_pipeline/results_<run_name>/
  scores/scores_uncond_<TICKER>_*.pkl
```

## Scoring Metrics (19/21)

9tok has no real order IDs → `time_to_cancel` and `log_time_to_cancel` are skipped.

Available: spread, orderbook_imbalance, log_inter_arrival_time, ask/bid_volume_touch, ask/bid_volume, limit_order_depth, cancellation_depth, limit_order_levels, cancellation_levels, vol_per_min, ofi, ofi_up/stay/down.

## Timing Estimates (1 node, 4 GPUs)

| Sequences | Est. inference | Est. scoring | Total |
|-----------|---------------|-------------|-------|
| 8 (test)  | ~30 min       | ~5 min      | ~35 min |
| 256       | ~5h           | ~30 min     | ~5.5h |
| 1024      | ~18h          | ~1.5h       | ~20h |

## Rules

- ALWAYS show config table before submitting
- ALWAYS confirm with user
- Default `--contiguous` for 1 node
- Use `≤4 nodes` per memory rule (feedback_lobbench_nodes.md)
- For quick tests: `N_SEQ=8 N_GEN=50 --time=00:30:00`
