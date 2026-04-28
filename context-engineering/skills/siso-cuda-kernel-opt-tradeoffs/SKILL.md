---
name: siso-cuda-kernel-opt-tradeoffs
description: Document SISO (Mamba3 state-space) CUDA FFI kernel optimization tradeoffs — N-split structural constraint (V buffer not split), union SMEM lifetimes, launch_bounds occupancy tuning, per-sample speedup saturation with BSZ. Use when tuning K3 kernel for different d_state values or similar state-scan kernels.
---

# SISO CUDA Kernel Optimization Tradeoffs

## When to Use

Tuning SISO/Mamba3 CUDA state-scan kernels (or similar state-scan patterns) where:
- `d_state` changes (e.g. 128→256→512), requiring SMEM rebudgeting
- Considering `SS_N_SPLITS` adjustment to improve occupancy
- Trying to free SMEM via buffer unioning
- Measuring per-sample throughput vs batch size

Triggers: "K3 kernel", "Mamba3 kernel", "state scan optimization", "N_SPLITS", "siso_state_scan", "d_state=", "SSM CUDA kernel".

## Kernel Structure (K3, Aramis's design)

```
Per-chunk loop (1625 iters at L=104k, CS=64):
  1. cp.async prefetch next chunk (K, V, Q, ADT)
  2. Cast state f32 → bf16 (state_cast buffer)
  3. Y_off = Q @ state_cast^T   (wmma_nt, output to Y_off SMEM buffer)
  4. Scale+write Y_off partial to HBM
  5. V_scaled = V * decay(a_cumsum)
  6. state *= exp(A_end)
  7. state += V_scaled^T @ K   (wmma_tn, UPDATE state in f32)

Grid: (N_SPLITS, H, B)
SMEM: state, state_cast, K_buf[2], V_buf[2], Q_buf[2], V_scaled, Y_off, a_cumsum
```

## Tradeoff 1: N_SPLITS Cannot Be Freely Increased

**V buffer is NOT split along N axis** — it's [CS][P] which has no N dimension. So each of `N_SPLITS` CTAs loads the FULL V buffer.

| N_SPLITS | V traffic | CTAs/H | Occupancy (SMEM limit) |
|----------|-----------|--------|-----------------------|
| 8 (SS_N=512) | 8x V loads | 96 | 2 CTAs/SM (96 KB/CTA) |
| 16 (SS_N=512) | **16x V loads** | 192 | 3 CTAs/SM (68 KB/CTA) |

**Empirical result at SS_N=512 DP=4×TP=2 production:**
- N_SPLITS=8: 2.41x speedup vs JAX
- N_SPLITS=16: **1.85x** (regression despite higher occupancy)

Root cause: V traffic doubling outweighed occupancy gain. HBM not compute-bound here — BW utilization ~10%, but V is the only duplicated tensor, so N_SPLITS multiplier hits it directly.

**Rule of thumb**: Keep N_SPLITS at minimum viable (`N_LOCAL = SS_N/SS_N_SPLITS ≥ WMMA_K=16`). Don't over-split unless V becomes negligible.

## Tradeoff 2: SMEM Union for Mutually-Exclusive Lifetimes

`state_cast` (written before wmma_nt at line 200) and `V_scaled` (written after wmma_nt completes at line 220) share NO overlap in use. Their memory can be unioned:

```cpp
struct StateScanSmem {
    float state[SS_P][SS_N_LOCAL];
    __nv_bfloat16 K_buf[2][SS_CS][SS_N_LOCAL];
    __nv_bfloat16 V_buf[2][SS_CS][SS_P];
    __nv_bfloat16 Q_buf[2][SS_CS][SS_N_LOCAL];
    float adt_buf[2][SS_CS];
    union {
        __nv_bfloat16 state_cast[SS_P][SS_N_LOCAL];   // used first
        __nv_bfloat16 V_scaled[SS_CS][SS_P];          // used after
    };
    float Y_off[SS_CS][SS_P];
    float a_cumsum[SS_CS];
};
```

Savings: `max(sizeof(state_cast), sizeof(V_scaled))` instead of sum. At SS_N=512, both are 8 KB → 8 KB/CTA saved (96→88 KB).

**Caveat**: Must verify lifetime non-overlap. Sync between writes must be explicit (`__syncthreads`). In K3, sync at line 207 guarantees all reads of `state_cast` complete before `V_scaled` writes.

**Empirical**: 2.41x → 2.43x (tiny improvement, correctness still 0.39% bf16 tol).

## Tradeoff 3: `__launch_bounds__` Hint Overrides SMEM Estimate

```cpp
__global__ void __launch_bounds__(SS_BLK, minBlocksPerSM)
siso_state_scan_kernel(...) { ... }
```

Second arg tells compiler to constrain register allocation so `minBlocksPerSM` CTAs can coexist. BUT:
- Does NOT increase SMEM/CTA limit — if SMEM forces 2 CTAs/SM, setting `minBlocksPerSM=3` is a failing hint.
- Can cause register spill if hint unrealistic (compiler reduces reg count aggressively).

**Rule**: Set `minBlocksPerSM` to `floor(228 KB / SMEM_per_CTA)` on GH200 Hopper.

## Tradeoff 4: SS_CS (chunk_size) Cannot Be Naively Doubled

At CS=64, SMEM ≈ 96 KB (SS_N=512). Double-buffered K/V/Q scale linearly with CS.

At SS_CS=128, double-buffered SMEM: ~192 KB → 1 CTA/SM. Viable only with single-buffering K/V/Q, which loses prefetch/compute overlap.

## Methodology: Per-Sample Speedup Saturation Curve

At fixed L, measure JAX vs K3 time across BSZ = [1, 2, 4, 8, 16, 32, 64]. Plot per-sample ms vs BSZ. The curve reveals:

- **B=1**: per-sample ≈ call time (~3-5 ms typical).
- **B=16-32**: saturation begins — kernel amortizes fixed overhead.
- **B=64+**: true peak throughput, speedup maxes out.

Example at SS_N=512 L=13056 single-GPU H=24:

| BSZ | JAX /sample (ms) | K3 /sample (ms) | Speedup |
|-----|------------------|-----------------|---------|
| 1   | 3.85 | 3.15 | 1.22x |
| 16  | 3.51 | 1.72 | 2.04x |
| 64  | 3.50 | 1.64 | **2.13x** |

K3 amortizes state-in-SMEM cost better (saturates at 1.6 ms/sample); JAX plateaus higher (3.5 ms/sample) due to XLA re-materialization.

## Verification Workflow

After kernel modification:
1. Rebuild: `bash m3_kernels/build_state_scan.sh`
2. Correctness: 2N DP=4×TP=2 benchmark checks max-rel-err vs single-GPU JAX. Bf16 tolerance ≈ 0.4%. Fail threshold: > 1%.
3. Performance: same benchmark reports `JAX P4+5+6` vs `K3 CUDA` p50 + speedup.
4. Peak memory: `measure_memory_subprocess.py` sweeps BSZ, reports peak GB.

## File Map (exp_R1g_mamba3_cuda_ffi)

| File | Role |
|------|------|
| `m3_kernels/src/state_scan_common.cuh` | SS_N, SS_CS, SS_P constants, WMMA helpers |
| `m3_kernels/src/siso_state_scan.cu` | Main kernel, SS_N_SPLITS, launch_bounds |
| `m3_kernels/src/reduce_y_off.cu` | Reduction of N_SPLITS partial Y_off |
| `s5/state_scan_ops.py` | Python wrapper, must match kernel constants |
| `test_k3_d512_2node.py` | 2N DP=4×TP=2 benchmark |
| `measure_memory_subprocess.py` | Max-BSZ + peak-memory sweep |

## Related

- `reference_jax_ffi_cuda_kernel_dev.md` — generic JAX FFI build/FFI register workflow
- `multi-node-jax-ffi-debug` skill — multi-node SLURM JAX distributed setup
