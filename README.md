# AutoResearch

**Paper to Three-Layer Verification in 48 Hours**

Given an arbitrary finance microstructure paper, an AI research agent reads it,
designs a three-layer verification pipeline, runs empirical replication on real
limit-order-book data, and publishes the results.

## Live Demo

[AutoResearch Landing Page](https://kangoxford.github.io/auto-quant-research/)

## Case Study: Dugast 2026

Replication of Dugast, Marta, Riva (2026) "Market Depth and Execution Delays" (SSRN 6440898).

**Paper finding:** beta(log depth to log delay) = 0.133 to 0.169 on NYSE

**Our replication:** beta = +0.2140 (SE 0.0106, t = 20.26)
- N = 46,094,530 limit orders
- 8 Nasdaq primary stocks, Q1 2025
- Time from PDF to first beta estimate: 12 minutes (SLURM job 4093982)

## How It Works

1. **PDF Ingestion**: pymupdf + LLM extracts regression spec and hypothesis
2. **9 Parallel Subagents**: dispatched in ~3 minutes, handle design and implementation
3. **~1000 lines of code generated**: `world_model/replay.py` + empirical replication script
4. **SLURM sbatch**: runs on GH200 ARM cluster, 46M orders analyzed
5. **Multi-channel publish**: Overleaf LaTeX, Notion (KaTeX), GitHub Pages

## Three-Layer Architecture

```
World Model (LOB simulator)
     |
     v
Teacher (IC-optimized depth-delay predictor)
     |
     v
Student (low-latency distilled, microsecond routing)
```

## Stack

- JAX 0.9 / Flax, Mamba3 (S5 SSM), PyTorch DataLoader
- statsmodels OLS, pandas, SLURM HPC (NVIDIA GH200 ARM)
- Claude Code CLI (Sonnet 4.6 main, Opus 4.7 subagents)
- pymupdf, Overleaf Git API, Notion REST API

## GitHub Pages Setup

1. Go to repo Settings > Pages
2. Set Source: Deploy from branch `main`, folder `/` (root)
3. Save. Site will be live at `https://kangoxford.github.io/auto-quant-research/`

## License

MIT
