# Explore Agent Output: SSM Fusion Opportunities Analysis

**Agent ID**: a20f5ed
**Model**: Opus 4.5
**Task**: Ultra-deep analysis of kernel fusion opportunities in SSM implementation
**Date**: 2025-12-29

---

## ULTRA DEEP ANALYSIS: Kernel Fusion Opportunities in SSM Implementation

Based on my comprehensive analysis of the codebase, here is the detailed report on kernel fusion opportunities that avoid the fatal flaw of M3C/M3D (custom_vjp activation caching).

---

## Executive Summary

**Root Cause of M3C/M3D Failure Confirmed:**
- `gelu_fused` (M3C) caches `x` in `_gelu_fused_fwd` (line 825: `return output, x`)
- `gate_residual_fused` (M3D) caches `(x_gelu, gate_logits)` in `_gate_residual_fused_fwd` (line 1155: `return output, (x_gelu, gate_logits)`)
- These cached activations: 24.6 MB + 24.6 MB = 49.2 MB per layer x 12 layers = **590 MB extra memory**
- XLA cannot see through `jt.triton_call` opaque operations, so no auto-rematerialization

**Recommended Priority Fusion Point: Steps 12-13 (D Feedthrough + Final Output) in ssm.py**

---

## Fusion Point 1: D Feedthrough + Output Cast (HIGHEST PRIORITY)

### Location
- **File**: `/lus/lfs1aip2/home/s5e/kangli.s5e/AlphaTrade/LOBS5/s5/ssm.py`
- **Lines**: 582-590

### Current Code
```python
# D feedthrough in FP32
Du = jax.vmap(lambda u: self.D * u)(input_fp32)  # Line 583
output = ys + Du                                  # Line 586
return output.astype(input_dtype)                 # Line 590
```

### Operations to Fuse
1. `self.D * u` - elementwise broadcast multiply: (H,) x (L, H) -> (L, H) FP32
2. `ys + Du` - elementwise add: (L, H) + (L, H) -> (L, H) FP32
3. `.astype(input_dtype)` - FP32 -> BF16 cast: (L, H) -> (L, H) BF16

### HBM Savings
- **Current writes**:
  - Du: 49.2 MB (L=12000, H=1024, FP32)
  - output (FP32): 49.2 MB
  - output (BF16): 24.6 MB
  - **Total: 123 MB / layer**

- **After fusion**:
  - output (BF16): 24.6 MB only
  - **Total: 24.6 MB / layer**

- **Savings: 98.4 MB / layer = 1,180.8 MB for 12 layers**

### Why This Works Without Custom VJP Caching

**Critical Analysis of Backward Pass Requirements:**

1. **`self.D` (learnable parameter)**: Always in HBM as model parameter - no caching needed
2. **`input_fp32`**: Already cached by JAX for the input path - it's the original input
3. **`ys` (scan output)**: MUST be cached by `jax.lax.associative_scan` for its backward pass

**Gradient Flow:**
```
output = ys + D * input
d_output = g  (upstream gradient)

d_ys = d_output  (identity)
d_D = sum(d_output * input, axis=0)  (reduce over L)
d_input = d_output * D  (broadcast)
```

**The key insight**: All three inputs (`ys`, `D`, `input_fp32`) are ALREADY cached for other reasons:
- `ys` is cached by the scan's backward pass
- `input_fp32` is the layer's input, cached for gradient computation
- `D` is a learned parameter, always in memory

**Therefore: NO ADDITIONAL custom_vjp caching is required!**

### Implementation Approach

**Option A: Triton Kernel (Simple Elementwise)**
```python
@triton.jit
def _ssm_output_fused_kernel(
    ys_ptr, input_ptr, D_ptr, output_ptr,
    L, H, BLOCK_SIZE: tl.constexpr
):
    """Fused: output[i,h] = bf16((ys[i,h] + D[h] * input[i,h]).astype(bf16))"""
    pid = tl.program_id(0)
    idx = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = idx < L * H

    row = idx // H
    col = idx % H

    ys = tl.load(ys_ptr + idx, mask=mask).to(tl.float32)
    inp = tl.load(input_ptr + idx, mask=mask).to(tl.float32)
    D = tl.load(D_ptr + col, mask=mask)  # Broadcast D[H] to (L, H)

    out = ys + D * inp
    tl.store(output_ptr + idx, out.to(tl.bfloat16), mask=mask)
```

**Option B: Pure JAX with jnp.add (Let XLA Fuse)**
```python
# Let XLA's fusion compiler handle it
output = (ys + self.D * input_fp32).astype(input_dtype)
# XLA SHOULD fuse this automatically, but may not due to vmap
```

### Risk Assessment
- **Risk Level**: LOW
- **Reasons**:
  1. Pure elementwise operations (no reductions, no complex dependencies)
  2. Same pattern as successful M3B kernel (GELU + Residual)
  3. All inputs already cached for other backward passes
  4. No custom_vjp caching required

### Recommended Priority: **P0** (Implement First)

---

## Fusion Point 2: C@xs Post-Processing (Steps 9-11)

### Location
- **File**: `/lus/lfs1aip2/home/s5e/kangli.s5e/AlphaTrade/LOBS5/s5/ssm.py`
- **Lines**: 325-329

### Current Code
```python
if conj_sym:
    ys = jax.vmap(lambda x: 2 * complex_matvec_bf16(C_tilde, x).real)(xs)
else:
    ys = jax.vmap(lambda x: complex_matvec_bf16(C_tilde, x).real)(xs)
```

Where `complex_matvec_bf16` does:
```python
def complex_matvec_bf16(A_complex, x_complex):
    A_re_bf, A_im_bf = _to_bf16_real_imag(A_complex)
    x_re_bf = x_complex.real.astype(np.bfloat16)
    x_im_bf = x_complex.imag.astype(np.bfloat16)
    rr = np.matmul(A_re_bf, x_re_bf)  # C_re @ xs_re
    ii = np.matmul(A_im_bf, x_im_bf)  # C_im @ xs_im
    ri = np.matmul(A_re_bf, x_im_bf)  # C_re @ xs_im
    ir = np.matmul(A_im_bf, x_re_bf)  # C_im @ xs_re
    real_bf = rr - ii
    imag_bf = ri + ir
    return real_bf.astype(np.float32) + 1j * imag_bf.astype(np.float32)
```

### Operations in Detail
1. Extract `xs.real` and `xs.imag` from complex64 -> FP32
2. Cast to BF16: `x_re_bf`, `x_im_bf`
3. 4x BF16 matmul: `rr`, `ii`, `ri`, `ir`
4. Subtract and add: `real_bf = rr - ii`, `imag_bf = ri + ir`
5. Cast back to FP32 and combine
6. Extract `.real` for output
7. Scale by 2 if `conj_sym`

### Fusion Opportunity
The post-matmul operations can be fused:
```
(rr - ii).astype(fp32) * 2  (if conj_sym)
```

But the 4 GEMMs cannot be easily fused (cuBLAS operations).

### HBM Savings
- **Partial fusion (post-GEMM)**: ~25 MB/layer
- Intermediate `rr`, `ii`, `ri`, `ir` writes could be avoided if using a custom complex GEMM kernel

### Custom VJP Caching Needed?
- **Maybe**: Depends on whether we recompute the intermediate GEMMs in backward
- If we use custom_vjp, we'd need to cache `xs` (complex64, 48.8 MB)

### Risk Assessment
- **Risk Level**: MEDIUM-HIGH
- **Reasons**:
  1. Involves GEMM operations - hard to fuse with Triton
  2. May require caching `xs` for backward pass
  3. Complex number operations add complexity

### Recommended Priority: **P2** (Lower priority)

---

## Fusion Point 3: B@u Complex Combine (Steps 3-5)

### Location
- **File**: `/lus/lfs1aip2/home/s5e/kangli.s5e/AlphaTrade/LOBS5/s5/ssm.py`
- **Line**: 312

### Current Code
```python
Bu_elements = jax.vmap(lambda u: complex_matvec_bf16_real_x(B_bar, u))(input_fp32)
```

Where `complex_matvec_bf16_real_x` does:
```python
def complex_matvec_bf16_real_x(A_complex, x_real):
    A_re_bf, A_im_bf = _to_bf16_real_imag(A_complex)
    x_bf = x_real.astype(np.bfloat16)
    real_bf = np.matmul(A_re_bf, x_bf)  # B_re @ u
    imag_bf = np.matmul(A_im_bf, x_bf)  # B_im @ u
    return real_bf.astype(np.float32) + 1j * imag_bf.astype(np.float32)
```

### Operations
1. Cast `B_bar` complex64 -> BF16 real/imag parts
2. Cast `input_fp32` -> BF16
3. 2x BF16 matmul
4. Cast back to FP32 and combine to complex64

### Fusion Opportunity
Similar to C@xs - post-GEMM operations can be fused, but GEMM itself is cuBLAS.

### HBM Savings
- **Partial**: ~12.3 MB/layer (intermediate Bu_re, Bu_im)

### Custom VJP Caching Needed?
- Less critical since input is already cached

### Risk Assessment
- **Risk Level**: MEDIUM
- GEMM fusion is complex

### Recommended Priority: **P2**

---

## Fusion Point 4: Lambda Broadcast Elimination (Step 6)

### Location
- **File**: `/lus/lfs1aip2/home/s5e/kangli.s5e/AlphaTrade/LOBS5/s5/ssm.py`
- **Line**: 309

### Current Code
```python
Lambda_elements = Lambda_bar * np.ones((input_fp32.shape[0], Lambda_bar.shape[0]))
```

### Problem
- Broadcasting `Lambda_bar` from (P,) to (L, P) wastes 48.8 MB
- Lambda_bar is only (P,) = 512 complex64 = 4 KB

### Fusion Opportunity
Modify `binary_operator` to read Lambda from constant memory or broadcast on-the-fly.

### HBM Savings
- **48.8 MB/layer** (eliminate broadcast write)

### Implementation Challenge
- Requires modifying `jax.lax.associative_scan` internals
- OR implementing custom parallel scan with constant Lambda

### Custom VJP Caching Needed?
- **YES**: Would need to implement custom backward for the modified scan

### Risk Assessment
- **Risk Level**: HIGH
- Requires changes to JAX core or custom scan implementation

### Recommended Priority: **P3** (Future work)

---

## Summary Table

| Fusion Point | Location | HBM Savings | Custom VJP Caching | Risk | Priority |
|-------------|----------|-------------|-------------------|------|----------|
| **D Feedthrough + Output** | ssm.py:582-590 | 98.4 MB/layer (1.18 GB total) | **NO** | LOW | **P0** |
| C@xs Post-Processing | ssm.py:325-329 | 25 MB/layer | Maybe | MEDIUM-HIGH | P2 |
| B@u Complex Combine | ssm.py:312 | 12.3 MB/layer | Less critical | MEDIUM | P2 |
| Lambda Broadcast | ssm.py:309 | 48.8 MB/layer | YES | HIGH | P3 |

---

## Recommended Action Plan

### Phase 1: Implement D Feedthrough Fusion (P0)

1. Create Triton kernel `_ssm_output_fused_triton_kernel` in `fused_kernels.py`
2. **DO NOT use custom_vjp** - let JAX auto-diff handle it
3. If JAX auto-diff fails (due to triton_call opacity), implement custom_vjp but **recompute forward values instead of caching**:

```python
@custom_vjp
def ssm_output_fused(ys, D, input_fp32):
    return _ssm_output_fwd_triton(ys, D, input_fp32)

def _ssm_output_fwd(ys, D, input_fp32):
    output = ssm_output_fused(ys, D, input_fp32)
    # CRITICAL: Don't cache output, only cache what's needed for gradient
    # All of ys, D, input_fp32 are already cached elsewhere!
    return output, ()  # Empty residuals!

def _ssm_output_bwd(_, g):
    # Recompute nothing - all inputs available from parent scope
    # This only works if we use closures properly
    pass
```

Actually, the cleanest approach:
```python
# Just use a simple fusion without custom_vjp
def ssm_output_fused(ys, D, input_fp32, output_dtype):
    """Fused: (ys + D * input).astype(output_dtype)"""
    # If Triton available, use kernel
    if TRITON_AVAILABLE:
        return _ssm_output_triton(ys, D, input_fp32, output_dtype)
    # JAX fallback
    return (ys + D * input_fp32).astype(output_dtype)
```

JAX will automatically handle the backward pass since:
- `ys` is already differentiated through the scan
- `D` is a parameter
- `input_fp32` is already differentiated

### Phase 2: Profile and Validate

1. Run with BSZ 16 (JAX baseline) and measure MFU
2. Enable D fusion and measure:
   - Peak HBM usage (should decrease by ~1.18 GB)
   - MFU (should remain ~13.9% or improve)
   - BSZ capacity (should allow BSZ 18-20)

---

## Why This Differs from M3C/M3D Failure

**M3C/M3D Pattern (Failed):**
```python
@custom_vjp
def gelu_fused(x):
    return _gelu_fwd_triton(x)

def _gelu_fused_fwd(x):
    output = gelu_fused(x)
    return output, x  # <-- CACHES x (24.6 MB)!
```

The problem: `x` is cached ONLY for the backward pass of GELU. It's not used anywhere else.

**D Feedthrough Pattern (Should Work):**
```python
# In S5SSM.__call__():
output = ys + self.D * input_fp32  # ys, D, input_fp32 all already cached
return output.astype(input_dtype)
```

Why it works:
- `ys` is cached by `associative_scan` for its backward pass (unavoidable, needed for scan gradients)
- `self.D` is a learnable parameter (always in memory)
- `input_fp32` is the layer input (already cached by JAX for input gradients)

**No new caching is introduced by the fusion!**

---

## Conclusion

**The D Feedthrough + Output Cast fusion (Steps 12-13) is the most promising opportunity because:**

1. **98.4 MB/layer savings** (1.18 GB total for 12 layers)
2. **NO custom_vjp caching needed** - all inputs already cached for other reasons
3. **Simple elementwise operations** - easy Triton kernel
4. **Low risk** - similar pattern to successful M3B kernel

This should allow increasing batch size from 6 (M3C/M3D failure) or 16 (JAX baseline) to potentially 18-20 while maintaining or improving MFU.
