---
name: eval-before-optimize
description: Before claiming RL/ES post-training improvements, verify eval precision exceeds expected signal magnitude. Prevents mistaking noise for learning.
version: 1.0.0
allowed-tools: Bash,Read,Grep,Agent
alwaysApply: false
---

# Eval Before Optimize

## When to Use

Trigger when:
- Starting any RL/ES/zeroth-order post-training experiment
- About to claim an IC/DA/reward improvement from post-training
- Eval metrics show high variance between runs of the same model

## Process

### Step 1: Measure Eval Noise Floor

Before ANY training, run the SAME model N times (N >= 10) on the SAME eval data:

```bash
# Pseudo-code: repeat eval K times with different random seeds
for seed in $(seq 1 20); do
    eval_model --checkpoint=BASE --seed=$seed --n_rollouts=256
done
# Compute std of the metric across runs
```

If `std(metric) > 0.5 * expected_improvement`, your eval cannot detect the improvement. Increase rollouts or change metric.

### Step 2: Compute Required Sample Size

```
IC standard error ≈ (1 - r²) / sqrt(n - 2)
For r ≈ 0.2, n = 15 pairs:  SE ≈ 0.26  (useless)
For r ≈ 0.2, n = 240 pairs: SE ≈ 0.06  (marginal)
For r ≈ 0.2, n = 1000 pairs: SE ≈ 0.03  (adequate)
```

Rule of thumb: need `SE < 0.25 * expected_signal` for 2-sigma detection.

### Step 3: Baseline Variance Check

Run baseline eval 5+ times. If the metric varies by more than your expected improvement, the experiment CANNOT produce a meaningful result regardless of algorithm.

### Step 4: Only Then Optimize

After confirming eval precision is adequate, proceed with post-training.

## Key Insights

1. **Noise masquerades as signal.** With 20 experiments x 5 eval points = 100 numbers, the "best" value will appear to show +100% improvement purely from noise. This is textbook p-hacking.

2. **The reward chain amplifies noise.** For LOB models: params → tokens → messages → orderbook → prices → returns → IC has 7 noise-amplifying stages. Perturbation signal (~0.01) becomes undetectable against IC noise (~0.10).

3. **Zeroth-order methods need deterministic rewards.** ES works for binary accuracy (Gan 2025) but not for noisy continuous metrics like Pearson IC. If `|fitness_change| < eval_noise`, the ES gradient is pure noise regardless of G, sigma, or optimizer.

4. **Greedy decoding is necessary but not sufficient.** Eliminates action-space noise but cannot fix the downstream measurement noise from orderbook simulation.

## Verification

- Baseline eval variance < 0.25 * expected signal
- Post-training metric has monotonic trend over 10+ steps (not spike-and-crash)
- Improvement survives when eval rollout count is doubled

## Origin

Extracted from R3-IC-ES experiment (2026-04-01 to 2026-04-03). 15+ experiments, ~200 GPU-hours. Initial "breakthrough" (IC +173%) was entirely eval noise, confirmed by 256-rollout high-precision experiment showing zero improvement over 24 steps.
