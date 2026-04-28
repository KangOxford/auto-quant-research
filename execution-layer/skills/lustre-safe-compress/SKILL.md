---
name: lustre-safe-compress
description: Compress Lustre directories with per-file safety pipeline (zstd → verify → rm) + multi-pass retry to handle OST quota races. Use when freeing storage on a Lustre filesystem at or near quota cap, especially when intermittent "Disk quota exceeded" causes silent .zst corruption with naive batch compression. Validated 2026-04-27 on sp500 ticker compression (4108 files, 332 GB raw → 18 GB zst, 18.4× ratio, 3-pass convergence).
version: 1.0.0
allowed-tools: Bash, Write, Edit, Read
alwaysApply: false
---

# Lustre Safe Compress with OST Quota Race Handling

## When to Use

Trigger on any of:

- Lustre filesystem at or near quota cap (`lfs quota` shows `*` after used / over hard limit), and you want to free space by replacing files with compressed copies
- Naive `zstd -r dir/` produces partial / silently-corrupt `.zst` files when filesystem is full
- HPC sbatch job for "compress + delete original" workflow (e.g. `.npy → .npy.zst` for sp500 tick data, log archives, snapshot rollups)
- "Compress one ticker per group, delete the .npy after, then move on" rolling migration patterns

Anti-pattern: do NOT use this when storage is plenty and naive `zstd -r` works. The safety pipeline adds verify+retry overhead unnecessarily.

## Why Standard zstd Fails on Full Lustre

| Naive approach | Failure mode |
|---|---|
| `zstd -r dir/` | Walks dir, when one .zst write hits "Disk quota exceeded", that .zst is partial / corrupt. **No detection** because zstd silently continues. Original .npy stays. Next read of corrupt .zst crashes user code with cryptic decompress error. |
| `for f in *.npy; do zstd -3 "$f" && rm "$f"; done` | Sequential. zstd success ≠ output integrity (it succeeds even if disk fills mid-write because it gets EIO async). Original deleted. **Permanent data loss**. |
| `zstd -r dir/ && rm -r dir/orig*.npy` | Same problem at ticker scale. Some .zst corrupt, original deleted, data lost. |

**Lustre-specific reason**: OST allocation is randomized per-file. When project quota is at cap, *some* OSTs still have a few GB free, others are saturated. Each new file write randomly lands on either, causing intermittent failures within the same job.

## The Safe Pipeline (per-file)

```bash
process_file() {
  local src="$1"           # /path/to/file.npy
  local dst="${src}.zst"   # /path/to/file.npy.zst

  # 1. Compress with retry (Lustre OST quota races)
  for i in 1 2 3; do
    if zstd -3 -q -f --keep "$src" -o "$dst" 2>/dev/null; then
      break
    fi
    sleep 2
  done
  if [ ! -f "$dst" ]; then
    echo "ZSTD_FAIL: $src" >&2
    return 1
  fi

  # 2. Verify integrity (decompress to /dev/null, check checksum)
  if ! zstd -t -q "$dst" 2>/dev/null; then
    echo "VERIFY_FAIL: $dst" >&2
    rm -f "$dst"  # remove corrupt output
    return 1
  fi

  # 3. Safe to delete original
  if ! rm -f "$src"; then
    echo "RM_FAIL: $src" >&2
    return 1
  fi
  return 0
}
export -f process_file
```

**Three invariants this guarantees**:

1. **No data loss**: original `.npy` only deleted after `.zst` verified intact. If verify fails, `.zst` is removed but `.npy` stays — file is exactly where it started.
2. **No orphan corrupt `.zst`**: failed verify removes the corrupt output, so retry runs see only good .zst files. No need to clean up between rounds.
3. **Idempotent**: re-running script on same dirs finds only remaining `.npy` (already-done files no longer match `*.npy` glob), so each pass naturally skips done work.

## Multi-Pass Retry Pattern

Since OST race causes intermittent failures, **expect to need 2-3 passes** on a quota-pressured filesystem. Failure rate decays exponentially as files get freed and OSTs balance:

```
Pass 1: 6.5% verify_fail (OST cap hit hardest)
Pass 2: 0.3% verify_fail (more headroom from pass 1 deletions)
Pass 3: 0% (clean)
```

The exit code convention: script returns `1` if any `.npy` remains after compress phase, `0` if 0 remaining. This signals to a wrapper to retry:

```bash
# Wrapper retry loop (sequential sbatch)
for ATTEMPT in 1 2 3 4 5; do
  sbatch --job-name=zst-${TICKER}-attempt${ATTEMPT} compress_tickers.batch
  # ... wait for job ... check exit code ...
  if [ "$EXIT" = "0:0" ]; then
    echo "Done after $ATTEMPT pass(es)"
    break
  fi
done
```

Or just submit one job and re-submit if exit != 0. Each pass is short (10s for 13 files, 3 min for 4000 files) so latency between passes is minor.

## Sbatch Skeleton

```bash
#!/bin/bash
#SBATCH --job-name=zst-compress-XXX
#SBATCH --nodes=1
#SBATCH --gres=gpu:1                # CPU-only but cluster requires GPU minimum
#SBATCH --cpus-per-task=64
#SBATCH --time=00:30:00             # 5-15min typical for ~300 GB raw

set -u
TICKERS="${TICKERS:-MO,HAL}"
ROOT="/lus/.../sp500"

# Pre-checks: tickers exist, NOT symlinks (only compress native dirs)
IFS=',' read -ra TICKER_ARR <<< "$TICKERS"
for T in "${TICKER_ARR[@]}"; do
  D="$ROOT/$T"
  [ -L "$D" ] && { echo "FATAL: $D is symlink"; exit 2; }
  [ ! -d "$D" ] && { echo "FATAL: $D missing"; exit 2; }
done

# Define process_file() (see Safe Pipeline section above)
process_file() { ... }
export -f process_file

# Build file list
FILE_LIST=/tmp/files_${SLURM_JOB_ID}.txt
> $FILE_LIST
for T in "${TICKER_ARR[@]}"; do
  ls "$ROOT/$T"/*.npy 2>/dev/null >> $FILE_LIST
done

# Parallel compress (32-thread xargs is good ratio of CPU utilization vs OST contention)
cat $FILE_LIST | xargs -P 32 -I{} bash -c 'process_file "$1"' _ {}

# Report
TOTAL_REMAINING=$(find $ROOT -maxdepth 2 -name '*.npy' | wc -l)
echo "Remaining: $TOTAL_REMAINING"
[ $TOTAL_REMAINING -gt 0 ] && exit 1 || exit 0
```

Reference: `/lus/lfs1aip2/projects/s5e/quant/AlphaTrade/LOBS5/compress_sp500_tickers.batch` (commit `c9eb775a` on `mamba3` branch) is the proven implementation.

## Symlink-Target Constraint (sp500-specific but generalizable)

When directories include **symlinks pointing OUT of the compressed root** (e.g. `sp500/PLTR -> /scratch/.../PLTR`), compress workflows need a CONSTRAINT: only `rm` originals in **native** dirs, NOT in symlink-target dirs (other consumers may still need the original `.npy`).

Pre-check pattern:

```bash
for T in "${TICKER_ARR[@]}"; do
  D="$ROOT/$T"
  if [ -L "$D" ]; then
    echo "SKIP_SYMLINK: $D points elsewhere; symlink-target rollout is a separate workflow"
    continue
    # Or for symlink-target dirs: zstd --keep but never rm .npy
  fi
  # ... compress + delete .npy ...
done
```

## Pre-Submit Checklist

Mandatory before sbatch:

1. `lfs quota -h -p <projid> /path` — confirm cap state, expected savings makes sense
2. `du -sh <dir>` — verify dir size matches expectation (catches symlink misclassification)
3. `[ -L "$dir" ]` test — sbatch script's pre-check rejects symlinks
4. Smoke test on smallest dir first — if MO+HAL works, scale to bigger pairs

## Verification

After job completes:

```bash
# 1. Count remaining .npy (should be 0)
for T in "${TICKER_ARR[@]}"; do
  N=$(ls $ROOT/$T/*.npy 2>/dev/null | wc -l)
  echo "[$T] $N .npy left"
done

# 2. Confirm .zst integrity (sample a few)
for f in $(ls $ROOT/*/${SAMPLE_TICKER}/*.npy.zst | shuf | head -5); do
  zstd -t -q "$f" && echo "OK: $f" || echo "BAD: $f"
done

# 3. Cross-check with Lustre quota
lfs quota -h -p <projid> /path  # used should drop by raw - zst delta
```

## Key Insights

1. **OST race is real but solvable**. Naive batch compress on full Lustre silently corrupts a fraction of files. Per-file verify + retry is the only safe pattern.

2. **Failure rate decays exponentially across passes**. Pass 1 ~5%, pass 2 ~0.5%, pass 3 ~0%. Don't bail on pass 1 partial success — script is idempotent, just re-submit.

3. **`zstd --keep -f -o $out`** is the right invocation: `--keep` preserves source until verify, `-f` overwrites partial output from prior failed attempt, `-o` is explicit (avoid `zstd file.npy` which produces `file.npy.zst` automatically — explicit is clearer when debugging).

4. **`zstd -t` not `zstd -d > /dev/null`**: `-t` is the dedicated test mode, faster than full decompress (verifies frame structure + checksum, no actual write).

5. **xargs -P 32 over -P 64**: too many parallel zstd workers worsen OST contention. 32 is empirically the sweet spot on this cluster (4108 files in 147s = 28 files/s aggregate at 32-way parallelism).

6. **18× compression on tick data is normal**: order book has heavy structural repetition (same prices/volumes across rows). Don't be surprised by ratios > 17×; conversely if ratio < 5× something's wrong (already-compressed data, encrypted, or random noise).

7. **Sbatch exit 1 ≠ failure**: When script returns 1 because of remaining files, that's *progress signal*, not bug. SLURM marks "FAILED" but the work was 95%+ successful. Just resubmit.

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Skip `--keep` on zstd | Source consumed before verify; verify_fail = data loss | Always `zstd -3 --keep` |
| Forget `export -f process_file` | xargs subshells can't see function | Add `export -f` after `process_file() { ... }` |
| `xargs -I{} zstd ...` directly | No verify, no retry, no rm logic | Wrap in bash function with full pipeline |
| Single sbatch run, give up on partial | 95% success thrown away by frustrated user | Re-submit until 0 remaining |
| Compress symlink-target dir's .npy then rm | Other consumers (other pipelines reading shared `lob_preproc/`) break | Pre-check `[ -L $dir ]` and skip rm step for symlink targets |
| Read live_jobs.md to track progress | Race conditions; CLAUDE.md says append-only | Use `cat >>` only, never edit |

## Related Skills

- **lustre-storage-audit**: Use BEFORE this skill to identify what to compress (which dirs are biggest, which are symlinks, where the big freeable wins are)
- **submit-job**: Use to wrap the sbatch submission with dedup check + commit-before-submit + monitor
- **moveon**: Use to restore monitors after session reconnect during long rollout (compressing 200+ ticker pairs may span multiple sessions)

## Reference Run

Validated 2026-04-27 on sp500 ticker compression:

| Job | Tickers | Files | Pass | Wall | Outcome |
|---|---|---|---|---|---|
| 4393167 | MO, HAL | 4108 | 1 | 147 s | 3841 ✓ + 267 verify_fail (kept .npy) |
| 4393180 | MO, HAL | 267 | 2 | 10 s | 254 ✓ + 13 verify_fail |
| 4393181 | MO, HAL | 13 | 3 | 2 s | 13 ✓ + 0 fail |

**Total**: 332 GB → 18 GB (18.4× ratio), 314 GB freed, 3 min compute, 0 data loss.

Quota progression: `200.3T*` → `200T*` (after pass 1) → `200T` (after pass 3, no longer over).
