# Auto Research: Resources Catalog

> **事实层 (Path C)**：Auto Research 所有 task 共享的 Simulator 代码、Checkpoint、数据资源索引。学生第一站。
>
> 全 task 共用，paper-task / model-task 都引用此文件作为路径来源。

## 1. Simulator 代码

### 1.1 主仓库 (LOBS5)
- **GitHub remote**: `git@github.com:KangOxford/LOBS5.git` (private at time of writing)
- **HPC clone (canonical)**: `/lus/lfs1aip2/projects/s5e/quant/AlphaTrade/LOBS5/`
- **架构**: JAX 0.9.0.1 / Flax / S5 (+ Mamba3 SISO replacement) + PyTorch DataLoader (CPU only)
- **核心文件 (一图速查)**:

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

### 1.2 关键 branch / worktree

| Branch / Worktree | Purpose | Path |
|---|---|---|
| `mamba3` | Mamba3 SISO 主开发分支（current HEAD `fc82838b` = R1g CUDA FFI default） | `LOBS5/` (current) |
| `exp/R1-Mamba3` | Mamba3 paper baseline 训练分支（commit `3f6d32a6` = pw8u0edj 用的版本） | `experiments/exp_R1_Mamba3/` |
| `shard-map` | 主开发分支（DiLoCo + 2D mesh） | `LOBS5/` other worktrees |
| `main` | 上游入口（很少更新） | `LOBS5/` mainline |

### 1.3 关键依赖

| Package | Version | Purpose |
|---|---|---|
| JAX | 0.9.0.1 | Compute backend (XLA) |
| jaxlib | 0.9.0.1 | Native runtime |
| Flax | (matches JAX 0.9.0.1) | NN module library |
| PyTorch | (CPU only) | DataLoader |
| Orbax | (Google) | Checkpoint format |
| NCCL | 2.29.3 (custom build) | ARM CAS fix, GH200 multi-node |
| AWS OFI NCCL | 1.18.0 | Slingshot-11 plugin |

Conda env: `/projects/s5e/quant/miniforge3` (base env)。Login 通过 `source ~/miniforge3/etc/profile.d/conda.sh` 加载。

## 2. Checkpoint 索引

> 19 GB 单 ckpt，HuggingFace upload pending（不在 GitHub repo 里）

### 2.1 mamba3 task SOTA (唯一)

| Field | Value |
|-------|-------|
| Wandb run | [`pw8u0edj`](https://wandb.ai/oxford-lob/mamba3/runs/pw8u0edj) |
| SLURM job | j3417629 (2026-03-28 02:04 UTC, by Aramis) |
| LOBS5 branch | `exp/R1-Mamba3` |
| LOBS5 commit | `3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28` |
| Worktree | `experiments/exp_R1_Mamba3/` |
| Ckpt path (HPC) | `experiments/exp_R1_Mamba3/checkpoints/j3417629_pw8u0edj_3417629/46050/` |
| Step | 46050 (last saved, 完整 19 GB) |
| IC@g=2000 | 0.102 |
| Public mirror | _TBD: HuggingFace upload pending_ |

详见 `models/mamba3.md`。

### 2.2 其他 task 的 SOTA ckpt

待回填（每个 paper task 的 reference replication 评估完成后）：

| Task | Ckpt status |
|---|---|
| Lillo & Farmer (2004) Hurst exponent | TBD — pending stylized fact replication |
| Toth et al. (2011) sqrt impact | TBD — pending impact analysis on mamba3-generated samples |
| Cont, Stoikov, Talreja (2009) LOB dynamics | TBD — pending stochastic process fit |

## 3. 数据索引

### 3.1 主训练数据 (mamba3 task 用)

| Field | Value |
|-------|-------|
| **路径 (HPC, canonical)** | `/lus/lfs1aip2/projects/s5e/lob_preproc_26tok` |
| **Encoding** | 26-token (base-100, vocab=2112) |
| **Tickers** | GOOG, AAPL, NVDA, AMZN, META, TSLA, MSFT, AMD (8) |
| **Train range** | 2022-01-01 至 2025-12-31 (4 yr) |
| **Test range** | 2026-01-01 至 2026-01-31 (held-out, 9 trading days) |
| **来源** | LOBSTER (NASDAQ ITCH-derived) → 内部 token preproc pipeline |
| **学生访问** | Contact Kang (kang.li@stats.ox.ac.uk) — LOBSTER 数据 NDA 内 |

> ⚠️ **注意**：旧 CLAUDE.md 写的 `GOOG_GOOGL_2016TO2021_24tok_preproc` (24-token) **已失效**。本 task 切换到 26-token 编码后路径变了，必须用上面 26tok 路径。

### 3.2 其他可用数据集

| Dataset | Path | Use case |
|---|---|---|
| MarS preproc (399M PyTorch model) | `/lus/lfs1aip2/projects/s5e/lob_preproc_mars` | bench-mars / return-bench-mars |
| MarS bench data variants | `/lus/lfs1aip2/projects/s5e/lob_pipeline/bench_data/mars-399m*` | Inline / cl / jaxob 比较 |
| JAN2023 GOOG 24tok | `/projects/s5e/quant/JAN2023/GOOG_24tok_preproc` | Legacy 24tok test data |
| LOBSTER 公开数据源 | https://lobsterdata.com | 学生学术使用，需要付费/申请 |

### 3.3 数据 schema (必须了解)

LOBSTER `*_message.csv` 列 (event-by-event):
1. `time` — fractional second since midnight
2. `event_type` — 1=submit, 2=cancel partial, 3=cancel full, 4=execute visible, 5=execute hidden
3. `order_id`
4. `size`
5. `price`
6. `direction` — +1 = buy-initiated, -1 = sell-initiated

LOBSTER `*_orderbook.csv` 列：每行是 message 之后的 LOB snapshot，500 levels each side (ask price/size, bid price/size, alternating)。

26-token encoding 把每条 message 转成 26 个 token (含 message fields + book quote levels at触发时刻)。具体见 `LOBS5/lob/encoding.py`。

## 4. 关键 metric 定义

| Metric | Definition | Computed where |
|---|---|---|
| **IC (Pearson IC)** | $\rho(\hat r_{t,t+g}, r_{t,t+g})$ across test samples | `eval_per_field_accuracy.py` |
| **Direction Accuracy** | $\frac{1}{N}\sum \mathbf{1}[\text{sign}(\hat r) = \text{sign}(r)]$ | LOBbench scripts |
| **Train loss** | next-token cross-entropy over vocab=2112 | wandb `train/loss` |
| **Hurst exponent** | DFA / R/S estimator on trade sign series | `tasks/papers/lillo_farmer_2004.md` 复现协议 |

> **不要算 Spearman IC** — 用户已多次明确：只看 Pearson IC。

## 5. HPC 环境 (学生用)

- **GPU**: NVIDIA GH200 Grace Hopper Superchip (ARM aarch64), 4× GPU/node, NV6 (6× NVLink bonded per pair)
- **Inter-node**: HPE Slingshot-11 (~200 Gbps, ~25 GB/s effective) — 不是 InfiniBand
- **Login node**: 不允许跑计算任务，只 git/edit/sbatch
- **Partition**: `workq`
- **Conda env path**: `/projects/s5e/quant/miniforge3`

### Sbatch 模板

```bash
sbatch --job-name=mamba3-paper-baseline-repro \
       --nodes=4 \
       --time=24:00:00 \
       --gres=gpu:4 \
       train_full_autoreg.batch
# 关键 env vars:
#   D_MODEL=1024 N_LAYERS=6 SSM_SIZE_BASE=1024 BLOCKS=16
#   PER_GPU_BSZ=4 SSM_TYPE=mamba3 OPT_CONFIG=muon
```

## 6. 引用本资源索引

```bibtex
@misc{auto_research_resources_2026,
  title={Auto Research Resources Catalog},
  author={Li, Kang and Fereydoun, Aramis},
  year={2026},
  note={Simulator code, checkpoints, and data references for KangOxford/auto-quant-research.},
  howpublished={\url{https://github.com/KangOxford/auto-quant-research/blob/main/RESOURCES.md}}
}
```

## 7. 维护说明

- 本文件**仅记录路径与索引**，具体的复现协议见各 task md 文件 (`tasks/papers/*.md`, `tasks/models/*.md`)
- 路径变化（如 `lob_preproc_26tok` 升级为 30tok）必须**同时更新本文件和所有引用 task md**
- HuggingFace upload 完成后，"Public mirror" 字段必须从 _TBD_ 改为实际 HF URL
