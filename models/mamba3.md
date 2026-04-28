# Task: mamba3

## Metadata
- **Task type**: Internal SOTA Model Card (not a paper replication)
- **Architecture**: Mamba3 SISO (Selective State Space, single-input single-output) replacing the S5 SSM layers in LOBS5
- **Training objective**: Token-level autoregressive next-token prediction on LOB message flow
- **Data**: 8 tickers × 4 yr (2022-2025), 26-token encoding, msg_seq_len=500
- **Maintainers**: kangli.s5e + aramis.s5e (Oxford LOB lab)

## TLDR (one line)
Built on the LOBS5 framework, replaces S5's diagonal complex SSM with a Mamba3 SISO selective state-space layer (per-token input-dependent $\Delta_t, B_t, C_t$), trained with Muon optimizer + hierarchical 2D mesh AllReduce on 4-node × 4-GPU for ~46k steps, achieving IC@g=2000 of **0.102**, which is the current baseline SOTA for the mamba3 task.

## Architecture and Configuration
**Backbone**: LOBS5 `PaddedLobPredModel` (message encoder + book encoder + fused trunk + decoder), with the SSM layers in the fused trunk swapped from S5 to Mamba3.

**Mamba3 SISO layer** (inside each SequenceLayer):
- $\Delta_t = \text{softplus}(W_\Delta x_t + b_\Delta)$ (input-dependent step size)
- $B_t = W_B x_t$, $C_t = W_C x_t$ (input-dependent state matrices)
- $A$ = HiPPO-LegS init, real-valued diagonal (`d_state=128`, `headdim=64`)
- Discretization: $\bar A = \exp(\Delta_t A)$, $\bar B = \Delta_t B_t$
- Recurrence: $h_t = \bar A h_{t-1} + \bar B x_t$, $y_t = C_t h_t$
- Pure JAX implementation (`use_triton=False`), using `jax.lax.scan` instead of a Triton kernel

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

> **Sole SOTA checkpoint**: `pw8u0edj` at **step 46050** (569 MB single step).
> Students reproducing results must use **this exact** ckpt + commit `3f6d32a6`. Other training runs are outside the SOTA scope of this task.

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

### Validation Metrics (Information Coefficient at multi-horizon, step 46050)

| Horizon (gap) | IC | Comment |
|---------------|-----|---------|
| g = 250 | 0.044 | short-horizon |
| g = 500 | 0.051 | mid-horizon |
| g = 1000 | 0.069 | long-horizon |
| g = 2000 | **0.102** | very long, mamba3 task SOTA |

> Note: IC = Pearson correlation between predicted and realized $r_{t,t+g}$. This is the core metric for the mamba3 task.

## Data Requirements
- **Tickers**: GOOG, AAPL, NVDA, AMZN, META, TSLA, MSFT, AMD (8 major NASDAQ large-cap stocks)
- **Train range**: 2022-01-01 to 2025-12-31 (4 years)
- **Test range**: 2026-01-01 to 2026-01-31 (held-out, 9 trading days)
- **Encoding**: 26-token (base-100, vocab includes book quote levels + msg fields)
- **Data root (HPC)**: `/lus/lfs1aip2/projects/s5e/lob_preproc_26tok`
  > ⚠️ Note: The old CLAUDE.md path `GOOG_GOOGL_2016TO2021_24tok_preproc` is no longer valid (24tok path). The mamba3 task uses the new 26tok path.
- **Data source**: LOBSTER (NASDAQ ITCH-derived) → internal token preproc pipeline (`lob_pipeline/`)

## Reproduction Protocol (student step-by-step)

### Step 1: clone LOBS5 + check out the correct commit
```bash
git clone git@github.com:KangOxford/LOBS5.git
cd LOBS5
git checkout 3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28
# or: git checkout exp/R1-Mamba3 (but branch HEAD may have advanced; pinning to the commit is preferred)
```

### Step 2: prepare data
- HPC internal users: read directly from `/lus/lfs1aip2/projects/s5e/lob_preproc_26tok/`
- External students: contact Kang (kang.li@stats.ox.ac.uk) for the LOBSTER 26tok preproc download link (data is under NDA and requires an academic use agreement)

### Step 3: load checkpoint
```python
import orbax.checkpoint as ocp
ckpt_path = "/lus/.../experiments/exp_R1_Mamba3/checkpoints/j3417629_pw8u0edj_3417629/46050"
mngr = ocp.CheckpointManager(ckpt_path)
state = mngr.restore(46050)
```

### Step 4: Eval (reproduce IC@g=2000=0.102)
```bash
python eval_per_field_accuracy.py \
    --restore /lus/.../checkpoints/j3417629_pw8u0edj_3417629/46050 \
    --eval_horizons 250,500,1000,2000 \
    --eval_dataset /lus/.../lob_preproc_26tok \
    --test_date_range 2026-01-01,2026-01-31
```

### Step 5: From-scratch retrain (verify reproducibility)
```bash
# Submit on 4-node × 4-GPU GH200
sbatch --nodes=4 --time=24:00:00 \
    --job-name=mamba3-paper-baseline-repro \
    train_full_autoreg.batch
# Key env vars: D_MODEL=1024 N_LAYERS=6 SSM_SIZE_BASE=1024 BLOCKS=16
#               PER_GPU_BSZ=4 SSM_TYPE=mamba3 OPT_CONFIG=muon
```

## Expected Results
- **Sanity check (1-node BSZ=2 smoke)**: train loss drops from ~10 to ~5 within 50 steps (loss in nats/token, vocab=2112)
- **Steady-state train loss**: ~0.6 at step 46050
- **IC@g=2000 on test 2026-01**: **0.10 ± 0.005** (paper baseline target)
- **Speed**: ~1.5 it/s on 4 nodes × 4 GH200 GPU (micro-batch 4 per GPU, 16 GPU total), ~660 ms per step
- **Train wall-time to step 46050**: ~8.5 hours

## Caveats / Notes for Students
- **MarS data is not an input for the mamba3 task** — that belongs to a separate generative simulator track; do not mix them up
- **Token mode must be 26tok** — 24tok is the deprecated legacy schema from earlier paper versions
- **Triton path is disabled** (`mamba3_use_triton=False`) — this SOTA was produced with pure JAX. Subsequent R1g defaults switched to CUDA FFI state-scan (commit `fc82838b`), but the paper baseline did not use it
- **Aramis's checkpoint lives in the shared worktree** (`exp_R1_Mamba3/`), not in the main LOBS5/checkpoints directory — students must supply the full path when reloading
- **Only one SOTA checkpoint is recognized for this task**: pw8u0edj@46050. Other mamba3 wandb runs (curriculum, etc.) are out of scope; students seeing additional runs in wandb should not confuse them with the canonical baseline

## References
- **Mamba3 paper**: _Mamba: Linear-Time Sequence Modeling with Selective State Spaces_ (Gu & Dao, 2023, arXiv:2312.00752), Mamba2/3 evolution
- **LOBS5 paper**: Lyu, Cohen, Cartea (2024) Generative Models for the Limit Order Book
- **S5 paper**: Smith, Warrington, Linderman (2023) Simplified State Space Layers for Sequence Modeling (ICLR)
- **Muon optimizer**: Jordan, Jin, Boza, Sun, Bernstein (2024) Muon (https://kellerjordan.github.io/posts/muon/)
- **HiPPO**: Gu, Dao, Ermon, Rudra, Re (2020) HiPPO (NeurIPS)

## Relationship to Other Auto-Research Tasks
- **Lillo & Farmer (2004)**: estimate the trade-sign Hurst exponent on mamba3-generated samples; expected $H \approx 0.7$ (validates whether the model captures long memory)
- **Toth et al. (2011)**: compute square-root market impact on mamba3-generated metaorders; expected $\beta \approx 0.5$
- **Cont, Stoikov, Talreja (2009)**: fit stochastic dynamics to mamba3-generated LOB shapes; results should match stylized facts

## Citing This Model Card
```bibtex
@misc{lobster_mamba3_2026,
  title={Mamba3 SISO Baseline on LOBSTER 26-token Encoding (Auto Research Internal SOTA)},
  author={Fereydoun, Aramis and Li, Kang},
  year={2026},
  note={Best Model So Far for mamba3 task. Wandb run pw8u0edj, LOBS5 commit 3f6d32a6, IC@g=2000=0.102.},
  howpublished={\url{https://github.com/KangOxford/auto-quant-research/blob/main/tasks/models/mamba3.md}}
}
```
