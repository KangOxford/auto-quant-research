# Critical Lessons - Never Repeat These Mistakes

## ❌ Double Sharding Disaster

### Mistake
Simultaneously using both:
1. `OrderbookDataset(rank=rank, world_size=world_size)` - file-level sharding
2. `DistributedSampler(num_replicas=world_size, rank=rank)` - sample-level sharding

### Consequence
**Data volume reduced by 16² = 256x!**

Each rank only trains on 412K samples (should be 106M / 16 = 6.6M)

### Correct Approach
**Use only one sharding mechanism**:

#### Option A: Only DistributedSampler (recommended)
```python
# Dataset - all ranks see the full data
dataset = OrderbookDataset(
    data_dir=...,
    # do NOT pass rank, world_size
)

# Sampler - responsible for partitioning
sampler = DistributedSampler(dataset, num_replicas=world_size, rank=rank)
```

#### Option B: File-level sharding only (only when preload-ram is needed)
```python
# Dataset - file-level partitioning
dataset = OrderbookDataset(rank=rank, world_size=world_size)

# Sampler - no partitioning (or num_replicas=1)
# Do not use DistributedSampler; use shuffle=True directly
```

### Verification
```python
# Check data volume per rank
total_samples_per_rank = len(dataset)
expected = total_dataset_size / world_size

assert abs(total_samples_per_rank - expected) < 0.1 * expected
```

## Remember
**DDP data loading shards only once!**
