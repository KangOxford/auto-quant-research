---
name: multi-node-jax-ffi-debug
description: Systematically debug multi-node JAX + custom CUDA FFI kernel failures under SLURM shard_map. Trigger on "multi-node JAX fails", "jax.distributed", "shard_map FFI", "2-node 8-GPU", "CUDA_ERROR_NO_DEVICE in srun", "No visible GPU devices".
version: 1.0.0
allowed-tools: Bash, Read, Write, Edit
alwaysApply: false
---

# Multi-node JAX + FFI Debugging (SLURM clusters)

## When to Use

Triggered when porting a single-GPU JAX FFI kernel to multi-node SLURM with `jax.distributed.initialize()` + `shard_map`, and hitting ANY of:
- `CUDA_ERROR_NO_DEVICE: no CUDA-capable device is detected` inside srun task
- `nvidia-smi -L` shows "No devices found" on compute node
- `jax.local_device_count() == 1` when expecting 4
- Rank 0 hangs at collective ops while rank 1 continues
- `FAILED_PRECONDITION: No visible GPU devices`

## The Six Failure Modes (in discovery order)

Each failure has a distinct symptom. Follow this order because fixing earlier ones reveals later ones.

### 1. env set in batch script doesn't propagate to srun

**Symptom:** Python inside srun fails with library-not-found or CUDA init error, even though `module load cuda` ran in batch.

**Root cause:** `module load`, `LD_LIBRARY_PATH`, conda activation only affect the batch process (usually runs on first node or login shell). `srun --export=ALL` propagates env vars but not re-resolves paths against each compute node's filesystem.

**Fix:** Move env setup into a wrapper script. Batch invokes `srun bash wrapper.sh`. Wrapper runs `module load`, sets `LD_LIBRARY_PATH`, then `exec python ...`.

```bash
# wrapper.sh (runs on EACH node inside srun)
export CONDA_PREFIX=/projects/s5e/quant/miniforge3
export PATH=$CONDA_PREFIX/bin:$PATH
module load cuda/12.6
NV_PKGS=$CONDA_PREFIX/lib/python3.12/site-packages/nvidia
export LD_LIBRARY_PATH="${NV_PKGS}/cusparse/lib:${NV_PKGS}/cublas/lib:..."
exec python your_script.py
```

### 2. `--exclusive` alone doesn't expose GPUs to srun tasks

**Symptom:** `nvidia-smi -L` in wrapper returns "No devices found" (not even an error).

**Root cause:** On some SLURM clusters (GH200 / Cray Slingshot), `--exclusive` reserves the node but does not set `CUDA_VISIBLE_DEVICES`. The srun task inherits an empty GPU set.

**Fix:** Add explicit GPU request to SBATCH directives:

```bash
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:4        # CRITICAL
#SBATCH --mem=0             # also recommended
#SBATCH --exclusive
```

Production `train_full_autoreg.batch` always uses `--gres=gpu:4`. Never omit.

### 3. `jax.distributed.initialize()` defaults to 1 local GPU

**Symptom:** `jax.local_device_count() == 1` but `nvidia-smi -L` shows 4.

**Root cause:** Without explicit `local_device_ids`, JAX auto-detects via `SLURM_LOCALID` which is per-process (always 0 when `--ntasks-per-node=1`). Result: JAX uses only 1 GPU per rank.

**Fix:** Pass `local_device_ids` explicitly:

```python
jax.distributed.initialize(
    coordinator_address=f"{first_node}:29500",
    num_processes=nnodes,
    process_id=proc_id,
    local_device_ids=[0, 1, 2, 3],  # all 4 local GPUs
)
```

After this: `jax.local_device_count() == 4`, `jax.device_count() == 8` (2 nodes x 4).

### 4. Collective operations must be called by ALL ranks

**Symptom:** Rank 0 hangs at `jnp.max(sharded_tensor)` while rank 1 continues past. Eventually deadlock or silent crash.

**Root cause:** JAX collective ops (`jnp.max`, `jnp.sum`, `.gather()`, etc.) on sharded tensors require ALL ranks to participate. Conditional-on-rank code breaks this.

```python
# WRONG - deadlocks
if proc_id == 0:
    diff = float(jnp.max(jnp.abs(sharded_out)))  # needs all ranks
    print(diff)

# CORRECT - all ranks compute, only rank 0 prints
diff = float(jnp.max(jnp.abs(sharded_out)))  # all participate
if proc_id == 0:
    print(diff)
```

Same rule for `jax.block_until_ready(x)` on sharded arrays.

### 5. Coordinator address via scontrol

**Symptom:** `jax.distributed.initialize` hangs or times out.

**Root cause:** Coordinator must be resolvable from all nodes. Using `hostname` gives local node name, not shared.

**Fix:** Resolve first allocated node in batch script, export via env:

```bash
FIRST_NODE=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -1)
export JAX_COORDINATOR_ADDRESS="${FIRST_NODE}:29500"
# srun inherits this env, wrapper reads it, python uses it
```

### 6. `jax.device_put(x, NamedSharding)` triggers multihost allgather OOM at 4N+

**Symptom:** Job runs fine through `jax.distributed.initialize()` and Mesh creation, then crashes on the FIRST `device_put` call with `RESOURCE_EXHAUSTED: Failed to allocate request for 76.17GiB`. Stack trace shows `multihost_utils.assert_equal -> process_allgather`. 2N works, 4N+ does not.

**Root cause:** `jax.device_put(x, NamedSharding)` when `x` is host-replicated (e.g. `jax.random.normal(key, shape)` produces same array on every host) calls `multihost_utils.assert_equal` to verify byte-equality across hosts. The verification uses `process_allgather` which materializes the FULL `B_global` tensor on every device. With B_global=8 at 4N (43 GB total) or B_global=16 at 8N (86 GB), this gather buffer exceeds GH200's 96 GB.

**Fix:** Use `jax.make_array_from_process_local_data` so each host generates only its own dp-axis shard. Bypass the cross-host equality check entirely. Use `jax.random.fold_in(key, jax.process_index())` for process-unique seeds (otherwise all hosts get identical shards which JAX still tolerates but defeats data-parallel testing).

```python
def _make_sharded(key, shape, spec, dtype, scale):
    sharding = NamedSharding(mesh, spec)
    n_proc = jax.process_count()
    proc_idx = jax.process_index()
    # Compute this process's local shard along the dp axis
    local_shape = list(shape)
    if spec[0] == 'dp':
        local_shape[0] = shape[0] // n_proc
    local_key = jax.random.fold_in(key, proc_idx)
    local_x = jax.random.normal(local_key, tuple(local_shape), dtype=dtype) * scale
    return jax.make_array_from_process_local_data(sharding, local_x, shape)
```

Verified at 4N (16 GPU) and 8N (32 GPU) on Isambard GH200: input prep completes in <1 second, K3 kernel runs and produces correct output (~0.7% rel err vs single-GPU JAX, within bf16 tolerance).

## Verified Working Pattern

This sequence of 6 fixes was verified on Isambard (GH200 Grace Hopper, Slingshot-11):
- 2-node 8-GPU benchmark with `shard_map(fn, mesh=(dp=4, tp=2))`: K3 vs JAX 2.43x speedup, rel err 0.39%
- 4-node 16-GPU benchmark with `mesh=(dp=8, tp=2)`: K3 vs JAX 2.39x speedup, rel err 0.70%
- 8-node 32-GPU benchmark with `mesh=(dp=16, tp=2)`: K3 vs JAX 2.37x speedup, rel err 0.70%

K3 speedup is essentially constant across DP scale because SISO heads are independent (no cross-GPU communication during state scan), so per-call SISO time is invariant to DP size.

## Checklist

When hitting multi-node JAX FFI issues, check in order:

1. [ ] Wrapper script in srun (env setup inside, not outside)
2. [ ] SBATCH `--gres=gpu:N --mem=0`
3. [ ] `jax.distributed.initialize(..., local_device_ids=[0..N-1])`
4. [ ] All ranks call collective ops (no `if rank == 0: jnp.max(...)`)
5. [ ] Coordinator from `scontrol show hostnames` not `hostname`

After all 5, `jax.device_count()` should equal `nnodes * local_gpus_per_node` and sharded computations should not deadlock.

## Verification

```python
# Sanity checks at top of script
assert jax.device_count() == expected_total
assert jax.local_device_count() == expected_local
print(f"[rank {proc_id}] devices: {jax.devices()}")

# Run a tiny sharded op before real benchmark
tiny = jax.device_put(jnp.ones((DP, TP, 4)), NamedSharding(mesh, P('dp','tp',None)))
result = jax.jit(shard_map(lambda x: x.sum(), mesh, in_specs=..., out_specs=...))(tiny)
assert float(result) == expected
```

## Related Files in Codebase

- `experiments/exp_R1g_mamba3_cuda_ffi/run_k3_2node_wrapper.sh` (wrapper pattern)
- `experiments/exp_R1g_mamba3_cuda_ffi/test_k3_tp2_2node.batch` (correct SBATCH directives)
- `experiments/exp_R1g_mamba3_cuda_ffi/test_k3_tp2_2node.py` (JAX distributed init + shard_map)
- `experiments/exp_R1_Mamba3/train_full_autoreg.batch` (production reference)
- `experiments/exp_R1_Mamba3/node_wrapper.sh` (production wrapper reference)
