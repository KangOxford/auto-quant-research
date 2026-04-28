# Auto Quant Research

**From Paper to Verified Replication in 48 Hours**

Auto Quant Research is a Human-in-the-Loop system for replicating quantitative microstructure papers. Hand it a paper; the system runs the replication while you sleep, publishes raw results to Notion, and pushes a polished version to Overleaf only after you have reviewed and signed off.

## Live Demo

[Auto Quant Research Landing Page](https://kangoxford.github.io/auto-quant-research/)

## Two Layers, Clear Boundaries

- **Execution Layer (Auto Research in Sleep)**: human-out-of-the-loop. The agent parses the paper PDF, dispatches parallel subagents to design the data pipeline and empirical regression spec, generates ~1k lines of code, commits to Git for full traceability, submits a SLURM batch job, monitors it to completion, and pushes raw results to Notion.
- **Decision Layer (Human in the Loop)**: surfaces only the choices that change the direction of the replication: which paper claim to test in depth, which ticker subset matters, which robustness check to add, which counter-narrative to highlight. The user reviews the auto-generated draft on Notion and edits or approves what they care most about proving.

## End-to-End Flow

1. **Push** raw results to Notion (Execution Layer auto-publishes).
2. **Review** on Notion (Decision Layer signoff).
3. **Wiki**: approved findings link into a growing Notion knowledge base, cross-referenced by paper, ticker, and stylized fact.
4. **Publish** to Overleaf only after user signoff, with each section tagged to the exact Git commit that produced it.

## The World Model

Every replication runs on top of the same World Model: a learned synthetic-market environment, calibrated against real Nasdaq order flow, that lets us synthesize counterfactual depth shocks, replay metaorders, and stress-test stylized facts. The World Model used here comes from the [sigma0](https://kangoxford.github.io/sigma0/) project. We deliberately treat the specific architecture as an implementation detail; future releases may swap in different sigma0 World Models without changing the replication interface.

## Examples Replicated

Each paper-replication example pins a specific Git commit so that reproductions anchor to an exact code state:

- **Dugast, Marta, Riva (2026)** "Market Depth and Execution Delays" (SSRN 6440898)
- **Lillo & Farmer (2004)** "The Long Memory of the Efficient Market"
- **Tóth et al. (2011)** "Anomalous Price Impact and the Critical Nature of Liquidity"
- **Cont, Stoikov, Talreja (2009)** "A Stochastic Model for Order Book Dynamics"

See [`papers/`](./papers/) for each paper's full replication spec, expected results, and reproduction protocol.

## Stack

- **Modeling & training**: JAX 0.9 / Flax, sigma0 World Model, PyTorch DataLoader, Orbax checkpointing, W&B
- **Empirical replication**: pandas + numpy, SLURM HPC (NVIDIA GH200 ARM), clustered SE / FE, py7zr
- **Orchestration & publishing**: Claude Code, pymupdf, Overleaf Git API, Notion REST API, GitHub Actions

## Repository Layout

```
auto-quant-research/
├── README.md                  ← you are here
├── RESOURCES.md               ← shared facts: simulator code, ckpt catalog, data refs
├── index.html                 ← the live landing page (deployed via GitHub Actions)
├── models/                    ← model cards (mamba3 / sigma0 World Model checkpoint)
├── papers/                    ← one .md per paper, with Best-Model-So-Far A/B/C tables
├── scripts/                   ← classical estimators (Hurst, sqrt-impact, etc.)
└── .github/workflows/         ← Pages deployment workflow
```

## License

MIT
