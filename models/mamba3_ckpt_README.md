# mamba3 SOTA Checkpoint — Download & Load Guide

This is the **single canonical checkpoint** for the `mamba3` task. Reproductions
of LOB next-token IC results (IC@g=2000 = 0.102) anchor to this artifact.

## Artifact

| Field | Value |
|-------|-------|
| **GitHub Release** | [`ckpt-mamba3-pw8u0edj-step46050`](https://github.com/KangOxford/auto-quant-research/releases/tag/ckpt-mamba3-pw8u0edj-step46050) |
| **File** | `mamba3_pw8u0edj_step46050.tar.zst` |
| **Compressed size** | 566.9 MB (zstd -19 of Orbax ckpt dir) |
| **Decompressed size** | ~569 MB (Orbax format) |
| **sha256** | `8cb798a57071e17f03b789d60cd1b6894dbad9d9fca05c51cc9425664550bc67` |

> **Why barely compressed?** Orbax `ocdbt` files are binary key-value stores
> of high-entropy fp32 / bf16 tensors. Compression headroom is < 1 %.

## Step 1: Download

### Option A — wget / curl (any platform)

```bash
wget https://github.com/KangOxford/auto-quant-research/releases/download/ckpt-mamba3-pw8u0edj-step46050/mamba3_pw8u0edj_step46050.tar.zst
```

```bash
curl -LO https://github.com/KangOxford/auto-quant-research/releases/download/ckpt-mamba3-pw8u0edj-step46050/mamba3_pw8u0edj_step46050.tar.zst
```

### Option B — `gh` CLI

```bash
gh release download ckpt-mamba3-pw8u0edj-step46050 \
  --repo KangOxford/auto-quant-research \
  --pattern '*.tar.zst'
```

## Step 2: Verify integrity

```bash
sha256sum mamba3_pw8u0edj_step46050.tar.zst
# Expected: 8cb798a57071e17f03b789d60cd1b6894dbad9d9fca05c51cc9425664550bc67
```

If the hash doesn't match, **redownload** — partial / corrupted file will
silently fail at Orbax restore time.

## Step 3: Decompress

### Linux / macOS

```bash
# Single command (streams without intermediate .tar)
zstd -d --stdout mamba3_pw8u0edj_step46050.tar.zst | tar -xf -

# Or in two steps if you don't have zstd's stdout mode
zstd -d mamba3_pw8u0edj_step46050.tar.zst   # produces .tar
tar -xf mamba3_pw8u0edj_step46050.tar
```

After extraction you should see:

```
46050/
├── _CHECKPOINT_METADATA
├── metadata/
└── state/
    ├── ocdbt.process_0/
    ├── ocdbt.process_1/
    ├── ...
    └── ocdbt.process_7/
```

### Need `zstd`?

```bash
# Ubuntu / Debian
sudo apt install zstd

# macOS
brew install zstd

# pip (Python wrapper)
pip install zstandard
```

## Step 4: Load with Orbax / JAX

```python
import jax
import orbax.checkpoint as ocp

ckpt_path = "/abs/path/to/46050"  # the directory you just extracted

# Option A: high-level CheckpointManager
mngr = ocp.CheckpointManager(ckpt_path)
state = mngr.restore(46050)

# Option B: low-level Checkpointer (for partial restore)
ckptr = ocp.PyTreeCheckpointer()
state = ckptr.restore(ckpt_path)

# state is a Flax TrainState-shaped pytree:
#   state.params       — model weights (Mamba3 SISO trunk + msg/book encoders + decoder)
#   state.opt_state    — Muon momentum buffers
#   state.step         — int; should be 46050
print(f"loaded step {state.step}")
```

## Step 5: Match the LOBS5 code state

This ckpt was trained on **LOBS5 commit `3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28`**
(branch `exp/R1-Mamba3`). To load it correctly, your client code must match
the Flax module structure at that commit:

```bash
git clone git@github.com:KangOxford/LOBS5.git
cd LOBS5
git checkout 3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28
```

If you load with a different commit's `PaddedLobPredModel` definition (e.g.,
HEAD of `mamba3` branch which is now CUDA FFI default), you'll hit shape /
dtype mismatches at restore time.

## Step 6: Run eval (sanity check IC@g=2000 = 0.102)

```bash
python eval_per_field_accuracy.py \
    --restore /abs/path/to/46050 \
    --eval_horizons 250,500,1000,2000 \
    --eval_dataset /lus/lfs1aip2/projects/s5e/lob_preproc_26tok \
    --test_date_range 2026-01-01,2026-01-31
```

Expected output:
```
g=250    IC=0.044
g=500    IC=0.051
g=1000   IC=0.069
g=2000   IC=0.102
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `OrbaxError: ckpt mismatch` | LOBS5 commit ≠ `3f6d32a6` | `git checkout 3f6d32a6` |
| `tar: ... unexpected EOF` | Corrupted download | re-download, verify sha256 |
| `JAX: cannot find device` | Local CPU has no GPU | run on a node with CUDA / Metal, or use `JAX_PLATFORMS=cpu` for slow inference |
| `vocab size mismatch` (2112) | Wrong token encoding | use 26-token preproc, not 24-token |

## Related

- [`models/mamba3.md`](mamba3.md) — full model card (architecture, training config, IC results)
- [`RESOURCES.md`](../RESOURCES.md) — shared facts layer (data paths, deps)
- [LOBS5 commit `3f6d32a6`](https://github.com/KangOxford/LOBS5/commit/3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28) — exact code state
