# Task: mamba3

## 元信息
- **任务类型**: Internal SOTA Model Card (非 paper replication)
- **架构**: Mamba3 SISO (Selective State Space, single-input single-output) 替换 LOBS5 的 S5 SSM 层
- **训练目标**: Token-level autoregressive next-token prediction on LOB message flow
- **数据**: 8 tickers × 4 yr (2022-2025), 26-token encoding, msg_seq_len=500
- **维护者**: kangli.s5e + aramis.s5e (Oxford LOB lab)

## TLDR (一句话)
基于 LOBS5 框架，把 S5 的 diagonal complex SSM 替换成 Mamba3 SISO 选择性 state-space 层（per-token 输入依赖的 $\Delta_t, B_t, C_t$），用 Muon optimizer + hierarchical 2D mesh AllReduce 在 4-node × 4-GPU 上训了 ~46k 步，IC@g=2000 达到 **0.102**，是当前 mamba3 task 的 baseline SOTA。

## 架构与配置
**Backbone**: LOBS5 `PaddedLobPredModel`（message encoder + book encoder + fused trunk + decoder），fused trunk 的 SSM 层从 S5 换成 Mamba3。

**Mamba3 SISO 层**（每个 SequenceLayer 内）:
- $\Delta_t = \text{softplus}(W_\Delta x_t + b_\Delta)$ (input-dependent step size)
- $B_t = W_B x_t$, $C_t = W_C x_t$ (input-dependent state matrices)
- $A$ = HiPPO-LegS init, real-valued diagonal (`d_state=128`, `headdim=64`)
- 离散化: $\bar A = \exp(\Delta_t A)$, $\bar B = \Delta_t B_t$
- Recurrence: $h_t = \bar A h_{t-1} + \bar B x_t$, $y_t = C_t h_t$
- Pure JAX 实现（`use_triton=False`），用 `jax.lax.scan` 而非 Triton kernel

**Trunk config**:
| Hyperparam | Value |
|------------|-------|
| d_model    | 1024  |
| n_layers   | 6     |
| ssm_size_base | 1024 |
| blocks     | 16    |
| activation | half_glu1 |
| prenorm    | True  |
| bidirectional | False |
| msg_seq_len | 500  |
| token_mode | 26tok |

**Optimizer**:
- Type: Muon (orthogonalized momentum on weight matrices) + AdamW for SSM params
- `muon_lr = 0.01`, `muon_wd = 0.005`
- `ssm_lr_base = 5e-4`, `lr_factor = 1.0`
- Warmup end fraction: 0.01, cosine annealing to 0
- `weight_decay = 0.005`, `p_dropout = 0.0`

**Distributed**:
- 4 nodes × 4 GPU (NVIDIA GH200 Grace Hopper, ARM)
- `micro_bsz = 4` per GPU, `num_devices = 4` (per-node count)
- `hierarchical = True` (2D mesh: NVLink intra + Slingshot-11 inter)
- `local_steps_k = 10` (DiLoCo-style local SGD between AllReduce)
- `grad_accum_steps = 1`

## Best Model So Far

> **唯一 SOTA checkpoint**: `pw8u0edj` 的 **step 46050** (569 MB single step).
> 学生 reproduce 必须使用 **这一个** ckpt + commit `3f6d32a6`，其他训练 run 不在本 task 的 SOTA 范围内。

| Field | Value |
|-------|-------|
| **Wandb run** | [`pw8u0edj`](https://wandb.ai/oxford-lob/mamba3/runs/pw8u0edj) |
| **Wandb project** | `oxford-lob/mamba3` |
| **SLURM job** | `j3417629` (started 2026-03-28 02:04 UTC) |
| **Author** | Aramis Fereydoun (`barrelman200`) |
| **LOBS5 git remote** | `git@github.com:KangOxford/LOBS5.git` |
| **LOBS5 branch** | `exp/R1-Mamba3` |
| **LOBS5 commit** | `3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28` |
| **Commit message** | `fix(mamba3): add batch dim for Triton path, remove broad except` |
| **Worktree dir (HPC)** | `/lus/lfs1aip2/projects/s5e/quant/AlphaTrade/experiments/exp_R1_Mamba3/` |
| **Checkpoint dir (HPC)** | `experiments/exp_R1_Mamba3/checkpoints/j3417629_pw8u0edj_3417629/` |
| **★ Use step** | **`46050`** (the last saved step) |
| **Full ckpt path (HPC)** | `experiments/exp_R1_Mamba3/checkpoints/j3417629_pw8u0edj_3417629/46050/` |
| **Single step size** | **569 MB** (Orbax dir; 34 saved steps total = 19 GB across the whole run dir but we keep only this one) |
| **Train length** | ~46050 steps × micro_bsz 4 × 16 GPU = ~2.95M token sequences seen |
| **Public mirror** | ✅ [GitHub Release `ckpt-mamba3-pw8u0edj-step46050`](https://github.com/KangOxford/auto-quant-research/releases/tag/ckpt-mamba3-pw8u0edj-step46050) — 567 MB tar.zst, sha256 `8cb798a570…0bc67`. See [`mamba3_ckpt_README.md`](mamba3_ckpt_README.md) for download + decompress + load. |

### 验证指标 (Information Coefficient at multi-horizon, step 46050)

| Horizon (gap) | IC | Comment |
|---------------|-----|---------|
| g = 250 | 0.044 | short-horizon |
| g = 500 | 0.051 | mid-horizon |
| g = 1000 | 0.069 | long-horizon |
| g = 2000 | **0.102** | very long, mamba3 task SOTA |

> Note: IC = Pearson correlation between predicted and realized $r_{t,t+g}$. 这是 mamba3 task 的核心 metric。

## 数据需求
- **Tickers**: GOOG, AAPL, NVDA, AMZN, META, TSLA, MSFT, AMD (8 个 NASDAQ 主流大盘股)
- **Train range**: 2022-01-01 至 2025-12-31 (4 年)
- **Test range**: 2026-01-01 至 2026-01-31 (held-out, 9 trading days)
- **Encoding**: 26-token (base-100, vocab 含书 quote levels + msg fields)
- **Data root (HPC)**: `/lus/lfs1aip2/projects/s5e/lob_preproc_26tok`
  > ⚠️ 注意：CLAUDE.md 旧版写的 `GOOG_GOOGL_2016TO2021_24tok_preproc` 已失效（24tok 路径），mamba3 task 用的是 26tok 新路径
- **数据源**: LOBSTER (NASDAQ ITCH-derived) → 内部 token preproc pipeline (`lob_pipeline/`)

## 复现协议 (学生 step-by-step)

### Step 1: clone LOBS5 + 切到正确 commit
```bash
git clone git@github.com:KangOxford/LOBS5.git
cd LOBS5
git checkout 3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28
# 或: git checkout exp/R1-Mamba3 (但 branch HEAD 可能已前进，optimal 是固定 commit)
```

### Step 2: 准备数据
- HPC 内部用户: 直接读 `/lus/lfs1aip2/projects/s5e/lob_preproc_26tok/`
- 外部学生: contact Kang (kang.li@stats.ox.ac.uk) 拿 LOBSTER 26tok preproc 的下载链接（数据在 NDA 内，需要走学术使用协议）

### Step 3: 加载 checkpoint
```python
import orbax.checkpoint as ocp
ckpt_path = "/lus/.../experiments/exp_R1_Mamba3/checkpoints/j3417629_pw8u0edj_3417629/46050"
mngr = ocp.CheckpointManager(ckpt_path)
state = mngr.restore(46050)
```

### Step 4: Eval (重现 IC@g=2000=0.102)
```bash
python eval_per_field_accuracy.py \
    --restore /lus/.../checkpoints/j3417629_pw8u0edj_3417629/46050 \
    --eval_horizons 250,500,1000,2000 \
    --eval_dataset /lus/.../lob_preproc_26tok \
    --test_date_range 2026-01-01,2026-01-31
```

### Step 5: From-scratch retrain (verify reproducibility)
```bash
# 在 4-node × 4-GPU GH200 上提交
sbatch --nodes=4 --time=24:00:00 \
    --job-name=mamba3-paper-baseline-repro \
    train_full_autoreg.batch
# 关键 env vars: D_MODEL=1024 N_LAYERS=6 SSM_SIZE_BASE=1024 BLOCKS=16
#                 PER_GPU_BSZ=4 SSM_TYPE=mamba3 OPT_CONFIG=muon
```

## 期望结果
- **Sanity check (1 节点 BSZ=2 smoke)**: 50 步内 train loss 从 ~10 降到 ~5（loss 单位是 nats/token in vocab=2112）
- **稳态 train loss**: ~0.6 at step 46050
- **IC@g=2000 on test 2026-01**: **0.10 ± 0.005** (paper baseline target)
- **Speed**: ~1.5 it/s on 4 nodes × 4 GH200 GPU (微批 4 per GPU, 16 GPU 总), 单 step ~660 ms
- **Train wall-time to step 46050**: ~8.5 hours

## Caveats / 学生注意
- **MarS data 不是 mamba3 task 的输入** — 那是另一条 generative simulator 线，不要混
- **Token 模式必须是 26tok** — 24tok 是 paper deprecated 的旧 schema
- **Triton path 是关闭的** (`mamba3_use_triton=False`) — 这次 SOTA 用的是 pure JAX。后续 R1g default 切到 CUDA FFI state-scan (commit `fc82838b`)，但 paper baseline 没用
- **Aramis 的 ckpt 在共享 worktree** (`exp_R1_Mamba3/`)，不是 LOBS5/checkpoints 主目录 — 学生跑 reload 要给完整路径
- **本 task 只认一个 SOTA ckpt**: pw8u0edj@46050。其他 mamba3 wandb run（curriculum 等）不在本 task 范围，学生看到 wandb 里有别的 run 不要混淆

## 参考资料
- **Mamba3 论文**: _Mamba: Linear-Time Sequence Modeling with Selective State Spaces_ (Gu & Dao, 2023, arXiv:2312.00752) 的 Mamba2/3 evolution
- **LOBS5 paper**: Lyu, Cohen, Cartea (2024) Generative Models for the Limit Order Book
- **S5 paper**: Smith, Warrington, Linderman (2023) Simplified State Space Layers for Sequence Modeling (ICLR)
- **Muon optimizer**: Jordan, Jin, Boza, Sun, Bernstein (2024) Muon (https://kellerjordan.github.io/posts/muon/)
- **HiPPO**: Gu, Dao, Ermon, Rudra, Re (2020) HiPPO (NeurIPS)

## 与其他 auto-research tasks 的关系
- **Lillo & Farmer (2004)**: 对 mamba3 generated samples 做 trade sign Hurst 估计，应得 $H \approx 0.7$（验证 long memory 是否被模型 capture）
- **Toth et al. (2011)**: 对 mamba3 生成的 metaorder 计算 square-root impact，应得 $\beta \approx 0.5$
- **Cont, Stoikov, Talreja (2009)**: 对 mamba3 生成的 LOB shape 做 stochastic dynamics 拟合，应匹配 stylized facts

## 引用本 model card
```bibtex
@misc{lobster_mamba3_2026,
  title={Mamba3 SISO Baseline on LOBSTER 26-token Encoding (Auto Research Internal SOTA)},
  author={Fereydoun, Aramis and Li, Kang},
  year={2026},
  note={Best Model So Far for mamba3 task. Wandb run pw8u0edj, LOBS5 commit 3f6d32a6, IC@g=2000=0.102.},
  howpublished={\url{https://github.com/KangOxford/auto-quant-research/blob/main/tasks/models/mamba3.md}}
}
```
