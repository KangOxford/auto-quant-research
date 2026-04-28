# Cont, Stoikov, Talreja (2009): A Stochastic Model for Order Book Dynamics

## Metadata
- **Authors**: Rama Cont, Sasha Stoikov, Rishi Talreja
- **Year**: 2009 (publ. 2010 in Operations Research)
- **Journal**: Operations Research, 58(3), 549-563
- **arXiv**: SSRN 1273160 (preprint, Sep 2008); paper DOI 10.1287/opre.1090.0780
- **Institution**: Columbia University (IEOR)

## TLDR (one sentence)
The LOB at each price level can be modelled as an independent birth-death queue; limit order arrival intensity decays with distance from the best quote as a power law $\lambda(i) = k / i^{\alpha}$; cancellation intensity is strictly proportional to queue size ($\theta(i) \cdot n$); market order arrivals are approximately Poisson; and all three event rates admit closed-form estimation from Level II high-frequency data.

## Core Stylized Facts
Based on Tokyo Stock Exchange Level II data, the paper establishes three empirical regularities governing LOB queue dynamics: (1) **limit order arrival intensity** at $i$ ticks from the opposite-side best quote decays as a power law $\lambda(i) = k / i^{\alpha}$, with empirical $\alpha$ on the order of 0.5 (Sky Perfect Communications $\alpha = 0.52$), while Bouchaud et al. report $\alpha \in [1.5, 2.5]$ in other markets; (2) **cancellation intensity** is strictly proportional to the queue size at that level, $\theta_{\text{total}}(i, n) = \theta(i) \cdot n$, meaning each resting order cancels independently with constant hazard rate $\theta(i)$, and $\theta(i)$ also decreases slowly with $i$; (3) **market order** arrivals are approximately a constant-intensity Poisson process with rate $\mu$ (Sky Perfect $\mu = 0.94$ in units of limit order size / minute). Together these three components form a birth-death queue, and the moment of best-quote change is precisely the first-passage time of that queue.

## Key Mathematics

**Limit order arrival intensity** ($i$ ticks from the opposite-side best):
$$
\lambda(i) = \frac{k}{i^{\alpha}}
$$

Empirical fit (least-squares on $i = 1,\dots,5$):
$$
\min_{k, \alpha} \; \sum_{i=1}^{5} \left( \hat{\lambda}(i) - \frac{k}{i^{\alpha}} \right)^{2}
$$
Sky Perfect Communications: $k = 1.92$, $\alpha = 0.52$ (units: limit-order-size blocks / minute). Cross-market studies by Bouchaud, Zovko, Farmer et al. report $\alpha \in [1.5, 2.5]$.

**Cancellation rate** (level $i$ with current queue size $x$):
$$
\theta_{\text{total}}(i, x) = \theta(i) \cdot x
$$
This assumes each resting order independently cancels with hazard rate $\theta(i)$, so the aggregate cancellation intensity is linear in queue size. Estimator:
$$
\hat{\theta}(i) = \frac{N_{c}(i)}{T \cdot Q_{i}}
$$
where $N_c(i)$ is the total number of cancellations at $i$ ticks from the best, and $Q_i$ is the steady-state average queue size at that level.

**Market order arrival**: independent Poisson on each side, rate $\mu$:
$$
\hat{\mu} = \frac{N_{m}}{T} \cdot \frac{S_{m}}{S_{l}}
$$
($S_m, S_l$ are the average sizes of market orders and limit orders respectively, used to convert market order counts into limit-order-size units).

**Probability of best-price change** = birth-death first-passage probability: given the current queue size, the probability that the queue drains (best price moves one tick) is given in closed form via Laplace transform in Section 4 of the paper; no Monte Carlo is required.

**Full Table 2 estimates for Sky Perfect Communications** (units: limit-order-size blocks / minute):

| $i$ | $\hat{\lambda}(i)$ | $\hat{\theta}(i)$ |
|-----|---------------------|---------------------|
| 1   | 1.85                | 0.71                |
| 2   | 1.51                | 0.81                |
| 3   | 1.09                | 0.68                |
| 4   | 0.88                | 0.56                |
| 5   | 0.77                | 0.47                |

$\hat{\mu} = 0.94$, $k = 1.92$, $\alpha = 0.52$。

## Data Requirements
- **Type**: Level II LOB data (best 5 levels each side), including trades + quotes timestamps
- **Granularity**: event-by-event (quote changes and trade timestamps accurate to second level)
- **Time span**: paper uses Tokyo Stock Exchange data (duration not quantified explicitly, denoted $T$ minutes); main table shows Sky Perfect Communications as a single-stock example
- **Data sources**: Tokyo Stock Exchange Level II (paper's original data); LOBSTER (Nasdaq, perfect match, message file directly distinguishes 4 event types), Nasdaq ITCH, NYSE OpenBook are all compatible
- **Key fields**: event type (limit submission / cancellation / market order), price level (tick distance from best), size, side, timestamp

## Replication Protocol (two things only — fit three rates)
1. Group LOBSTER message file by event type, compute average sizes $S_m, S_l, S_c$ for each of the three event classes, and adopt $S_l$ as the size unit (one size-$S_l$ block counts as one event)
2. **Limit arrival rate** $\lambda(i)$:
   - For each distance $i = 1, 2, \dots, 10$ (tick distance from the opposite-side best), compute $\hat{\lambda}(i) = N_l(i) / T$ (number of limit orders per unit time at distance $i$)
   - Perform log-log least-squares fit on $i = 1,\dots,5$ to obtain $k, \alpha$
   - Verify: $\log \hat{\lambda}(i)$ vs $\log i$ should fall on a straight line
3. **Cancellation rate** $\theta(i)$:
   - First estimate steady-state queue size $Q_i$ (average size across Level II quote rows, divided by $S_l$)
   - $\hat{\theta}(i) = N_c(i) / (T \cdot Q_i)$ — cancellation frequency divided by queue size, yielding the per-order hazard rate directly
   - Verify linearity: plot cancel count across different $Q$ bins; should fall on a line through the origin
4. **Market order rate** $\mu$:
   - $\hat{\mu} = (N_m / T) \cdot (S_m / S_l)$ (normalize market orders into limit-size units)
   - Verify Poisson property: check whether inter-arrival times are approximately exponentially distributed
5. Use the fitted $(\lambda, \mu, \theta)$ to simulate the birth-death queue, apply the Laplace transform (paper Section 4) to compute the best-price first-passage distribution, and compare against the empirical best-quote change time distribution from actual LOB data

## Expected Results
- **Key numbers** (reproducing Sky Perfect order of magnitude):
  - $\alpha \in [0.5, 2.5]$ (limit arrival decay exponent; large variation across stocks/markets: Sky Perfect 0.52, Zovko-Farmer/Bouchaud 1.5–2.5)
  - $\mu \approx O(\text{1 / minute})$ for liquid stocks (Sky Perfect 0.94)
  - $\theta(i) \approx 0.4 - 0.8$ per limit-order-size block / minute (Sky Perfect 0.47–0.81), stable per ticker
- **Plots**:
  - $\log \hat{\lambda}(i)$ vs $\log i$ — approximately linear (Figure 1a, distances 1–10 ticks)
  - $\hat{\theta}(i) \cdot Q_i$ (observed cancel rate) vs queue size — should pass through the origin as a straight line
  - market order inter-arrival CDF — exponential (Poisson test)

## Reference Implementations
- **Public code**: the paper itself has no open-source code; see the stochastic LOB module in ABIDES (agent-based interactive discrete event simulator, Byrd et al. 2020), as well as teaching libraries such as mlofi / lob_inference
- **Replication difficulty**: ⭐⭐ (all estimators are univariate statistics; the only challenge is correctly splitting event types and computing distance-to-best from the raw message file)
- **Data availability**: high (LOBSTER provides data directly; we already have 8 tickers × 4 years)

## Correspondence with Our LOBSTER Data
- **LOBSTER message file event types**:
  - 1 = new limit order submission → goes into $N_l(i)$
  - 2 = partial cancellation → goes into $N_c(i)$ (scaled by cancel size / $S_l$)
  - 3 = full cancellation/deletion → goes into $N_c(i)$
  - 4 = visible execution (market order) → goes into $N_m$
  - 5 = hidden execution → explicitly ignored by the paper (hidden / iceberg orders do not affect the best quote)
- Perfect correspondence with the paper's three event classes: limit / cancel / market
- Distance to best is computed directly from message price minus best bid/ask, divided by tick size
- **Directly actionable**: one stock for one day (~5e5 events) allows a complete estimator implementation in a few minutes of Python pandas; our 4 years × 8 tickers data is sufficient to cross-validate the stability of $\alpha, \mu, \theta$

## Best Model So Far

> **Task core numbers**: empirical estimates of the three rates $(\lambda, \mu, \theta)$ + power-law decay exponent $\alpha$
>
> Auto Research three columns (paper / classical / mamba3-generated):

| Stream | Source | $\hat \alpha$ | $\hat \mu$ | $\hat \theta(i=1)$ | Status |
|--------|--------|---------------|------------|---------------------|--------|
| **A. Reference (paper)** | Sky Perfect Communications, TSE Level II | 0.52 | 0.94 | 0.71 | published |
| **B. Classical estimator on LOBSTER** | 8 tickers × 4 yr, event-type split + log-log fit + cancel hazard | TBD | TBD | TBD | _pending — ~5e5 events per stock per day, runs in a few minutes of Python_ |
| **C. mamba3 generated samples** | same estimator applied to mamba3 SOTA generated message stream | TBD | TBD | TBD | _pending — uses mamba3 ckpt pw8u0edj@46050_ |

**Associated model card**: the checkpoint used to evaluate mamba3 generated samples is documented in [`models/mamba3.md`](../models/mamba3.md) at step 46050 of pw8u0edj.

**Checkpoint + commit pinning for replication**:
```bash
git clone git@github.com:KangOxford/LOBS5.git
cd LOBS5
git checkout 3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28   # mamba3 paper baseline state
# generate per-ticker per-day message stream → group by event_type ∈ {1,2,3,4,5} → fit three rates
```

**Expected verdict**:
- Stream B (real LOBSTER): $\hat \alpha \in [0.5, 2.5]$ (large variation across stocks/markets), $\hat \mu \sim 1$/min, $\hat \theta(1) \in [0.4, 0.8]$ ✓
- Stream C (mamba3): the three rates should be numerically close to Stream B when compared on the **same ticker, same day** → mamba3 captures birth-death queue dynamics;
  otherwise the generative model distorts the relative frequencies of limit/cancel/market event types

## Citation
```bibtex
@article{cont2010stochastic,
  title={A stochastic model for order book dynamics},
  author={Cont, Rama and Stoikov, Sasha and Talreja, Rishi},
  journal={Operations Research},
  volume={58},
  number={3},
  pages={549--563},
  year={2010},
  publisher={INFORMS},
  doi={10.1287/opre.1090.0780}
}
```
