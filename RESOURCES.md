# Auto Research: Resources Catalog

> **Fact Layer (Path C)**: Shared index of Simulator code, checkpoints, and data resources across all Auto Research tasks. The starting point for new students.
>
> Shared across all tasks; both paper-tasks and model-tasks reference this file as the canonical path source.

## 1. Simulator Code

### 1.1 Main repository (LOBS5)
- **GitHub remote**: `git@github.com:KangOxford/LOBS5.git` (private at time of writing)
- **HPC clone (canonical)**: `/lus/lfs1aip2/projects/s5e/quant/AlphaTrade/LOBS5/`
- **Architecture**: JAX 0.9.0.1 / Flax / S5 (+ Mamba3 SISO replacement) + PyTorch DataLoader (CPU only)
- **Key files (quick reference)**:

| File | Role |
|------|------|
| `run_train.py` | Entry point — CLI args, jax.distributed init |
| `lob/train.py` | Training loop, mini-epochs, validation, checkpointing |
| `lob/train_helpers.py` | JIT'd train_step / eval_step, optimizer, LR schedule |
| `lob/init_train.py` | Model init, Orbax checkpoint load/save |
| `lob/sharding_utils.py` | JAX mesh (1D flat / 2D hierarchical), data + param sharding |
| `lob/dataloading.py` | Dataset factory, multi-ticker, distributed sampler |
| `lob/lobster_dataloader.py` | LOBSTER_Dataset (PyTorch Dataset), file caching, masking |
| `lob/encoding.py` | Message_Tokenizer (24/26-token, base-100, vocab=2112) |
| `lob/lob_seq_model.py` | PaddedLobPredModel (Flax module, production model) |
| `s5/ssm.py` | S5 state space model core (HiPPO-LegS init, ZOH discretize) |
| `s5/layers.py` | SequenceLayer (PreNorm + S5 / Mamba3 + half_glu1 + skip) |
| `lob/inference.py` | Autoregressive generation with error correction |

### 1.2 Key branches / worktrees

| Branch / Worktree | Purpose | Path |
|---|---|---|
| `mamba3` | Mamba3 SISO main development branch (current HEAD `fc82838b` = R1g CUDA FFI default) | `LOBS5/` (current) |
| `exp/R1-Mamba3` | Mamba3 paper baseline training branch (commit `3f6d32a6` = version used by pw8u0edj) | `experiments/exp_R1_Mamba3/` |
| `shard-map` | Main development branch (DiLoCo + 2D mesh) | `LOBS5/` other worktrees |
| `main` | Upstream entry point (rarely updated) | `LOBS5/` mainline |

### 1.3 Key dependencies

| Package | Version | Purpose |
|---|---|---|
| JAX | 0.9.0.1 | Compute backend (XLA) |
| jaxlib | 0.9.0.1 | Native runtime |
| Flax | (matches JAX 0.9.0.1) | NN module library |
| PyTorch | (CPU only) | DataLoader |
| Orbax | (Google) | Checkpoint format |
| NCCL | 2.29.3 (custom build) | ARM CAS fix, GH200 multi-node |
| AWS OFI NCCL | 1.18.0 | Slingshot-11 plugin |

Conda env: `/projects/s5e/quant/miniforge3` (base env). Loaded on login via `source ~/miniforge3/etc/profile.d/conda.sh`.

## 2. Checkpoint Index

> Single checkpoint is 19 GB; HuggingFace upload pending (not in the GitHub repo).

### 2.1 mamba3 task SOTA (sole checkpoint)

| Field | Value |
|-------|-------|
| Wandb run | [`pw8u0edj`](https://wandb.ai/oxford-lob/mamba3/runs/pw8u0edj) |
| SLURM job | j3417629 (2026-03-28 02:04 UTC, by Aramis) |
| LOBS5 branch | `exp/R1-Mamba3` |
| LOBS5 commit | `3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28` |
| Worktree | `experiments/exp_R1_Mamba3/` |
| Ckpt path (HPC) | `experiments/exp_R1_Mamba3/checkpoints/j3417629_pw8u0edj_3417629/46050/` |
| Step | 46050 (last saved, full 19 GB) |
| IC@g=2000 | 0.102 |
| Public mirror | _TBD: HuggingFace upload pending_ |

See `models/mamba3.md` for details.

### 2.2 SOTA checkpoints for other tasks

To be filled in (after each paper task's reference replication evaluation is complete):

| Task | Ckpt status |
|---|---|
| Lillo & Farmer (2004) Hurst exponent | TBD — pending stylized fact replication |
| Toth et al. (2011) sqrt impact | TBD — pending impact analysis on mamba3-generated samples |
| Cont, Stoikov, Talreja (2009) LOB dynamics | TBD — pending stochastic process fit |

## 3. Data Index

### 3.1 Primary training data (used by mamba3 task)

| Field | Value |
|-------|-------|
| **Path (HPC, canonical)** | `/lus/lfs1aip2/projects/s5e/lob_preproc_26tok` |
| **Encoding** | 26-token (base-100, vocab=2112) |
| **Tickers** | GOOG, AAPL, NVDA, AMZN, META, TSLA, MSFT, AMD (8) |
| **Train range** | 2022-01-01 to 2025-12-31 (4 yr) |
| **Test range** | 2026-01-01 to 2026-01-31 (held-out, 9 trading days) |
| **Source** | LOBSTER (NASDAQ ITCH-derived) → internal token preprocessing pipeline |
| **Student access** | Contact Kang (kang.li@stats.ox.ac.uk) — LOBSTER data covered by NDA |

> ⚠️ **Note**: The path `GOOG_GOOGL_2016TO2021_24tok_preproc` (24-token) recorded in the old CLAUDE.md is **no longer valid**. This task switched to 26-token encoding, which changed the path — you must use the 26tok path above.

### 3.2 Other available datasets

| Dataset | Path | Use case |
|---|---|---|
| MarS preproc (399M PyTorch model) | `/lus/lfs1aip2/projects/s5e/lob_preproc_mars` | bench-mars / return-bench-mars |
| MarS bench data variants | `/lus/lfs1aip2/projects/s5e/lob_pipeline/bench_data/mars-399m*` | Inline / cl / jaxob comparison |
| JAN2023 GOOG 24tok | `/projects/s5e/quant/JAN2023/GOOG_24tok_preproc` | Legacy 24tok test data |
| LOBSTER public source | https://lobsterdata.com | Academic use by students; requires payment / application |

### 3.3 Data schema (required reading)

LOBSTER `*_message.csv` columns (event-by-event):
1. `time` — fractional second since midnight
2. `event_type` — 1=submit, 2=cancel partial, 3=cancel full, 4=execute visible, 5=execute hidden
3. `order_id`
4. `size`
5. `price`
6. `direction` — +1 = buy-initiated, -1 = sell-initiated

LOBSTER `*_orderbook.csv` columns: each row is the LOB snapshot immediately after a message, with 500 levels per side (ask price/size, bid price/size, alternating).

The 26-token encoding converts each message into 26 tokens (covering message fields + book quote levels at the time of the event). See `LOBS5/lob/encoding.py` for details.

## 4. Key metric definitions

| Metric | Definition | Computed where |
|---|---|---|
| **IC (Pearson IC)** | $\rho(\hat r_{t,t+g}, r_{t,t+g})$ across test samples | `eval_per_field_accuracy.py` |
| **Direction Accuracy** | $\frac{1}{N}\sum \mathbf{1}[\text{sign}(\hat r) = \text{sign}(r)]$ | LOBbench scripts |
| **Train loss** | next-token cross-entropy over vocab=2112 | wandb `train/loss` |
| **Hurst exponent** | DFA / R/S estimator on trade sign series | `tasks/papers/lillo_farmer_2004.md` replication protocol |

> **Do not compute Spearman IC** — the user has repeatedly stated: only Pearson IC is used.

## 5. HPC environment (for students)

- **GPU**: NVIDIA GH200 Grace Hopper Superchip (ARM aarch64), 4× GPU/node, NV6 (6× NVLink bonded per pair)
- **Inter-node**: HPE Slingshot-11 (~200 Gbps, ~25 GB/s effective) — not InfiniBand
- **Login node**: no compute tasks permitted; git/edit/sbatch only
- **Partition**: `workq`
- **Conda env path**: `/projects/s5e/quant/miniforge3`

### Sbatch template

```bash
sbatch --job-name=mamba3-paper-baseline-repro \
       --nodes=4 \
       --time=24:00:00 \
       --gres=gpu:4 \
       train_full_autoreg.batch
# Key env vars:
#   D_MODEL=1024 N_LAYERS=6 SSM_SIZE_BASE=1024 BLOCKS=16
#   PER_GPU_BSZ=4 SSM_TYPE=mamba3 OPT_CONFIG=muon
```

## 6. Citing this resource catalog

```bibtex
@misc{auto_research_resources_2026,
  title={Auto Research Resources Catalog},
  author={Li, Kang and Fereydoun, Aramis},
  year={2026},
  note={Simulator code, checkpoints, and data references for KangOxford/auto-quant-research.},
  howpublished={\url{https://github.com/KangOxford/auto-quant-research/blob/main/RESOURCES.md}}
}
```

## 7. Maintenance notes

- This file **records paths and indexes only**; specific replication protocols are in the individual task markdown files (`tasks/papers/*.md`, `tasks/models/*.md`).
- Any path change (e.g., `lob_preproc_26tok` upgraded to 30tok) must be **reflected in this file and all referencing task md files simultaneously**.
- Once the HuggingFace upload is complete, the "Public mirror" field must be updated from _TBD_ to the actual HF URL.
