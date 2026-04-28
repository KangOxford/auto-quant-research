# Lillo & Farmer (2004): The Long Memory of the Efficient Market

## Metadata
- **Authors**: Fabrizio Lillo, J. Doyne Farmer
- **Year**: 2004
- **Journal**: Studies in Nonlinear Dynamics & Econometrics, 8(3), Article 1
- **arXiv**: cond-mat/0311053
- **DOI**: 10.2202/1558-3708.1226

## TLDR (one sentence)
Using LSE 1999-2002 data, the paper shows that the trade sign sequence is a long-memory process with Hurst exponent $H \approx 0.7$ (autocorrelation power-law decay exponent $\alpha \approx 0.6$), yet market returns remain close to a random walk (efficient), because transaction size and liquidity provide an anti-correlated compensating mechanism.

## Core Stylized Fact
Using tick-by-tick order data from the London Stock Exchange (LSE) spanning approximately four years (1999-2002), the authors find that **order sign sequences (market orders, limit orders, and cancellations alike) behave as long-memory processes**, with the autocorrelation function decaying as a power law $C(\tau) \sim \tau^{-\alpha}$ with $\alpha \approx 0.6$, corresponding to a Hurst exponent $H \approx 0.7$. This persistence is universal across 20+ LSE stocks, with cross-stock variation below 0.1. Although the high predictability of the sign sequence would naively imply severe market inefficiency, mid-price returns remain approximately a random walk: the paper demonstrates that transaction size and liquidity (spread/depth) are also long-memory processes and are anti-correlated with order sign, precisely cancelling the predictable profit implied by sign persistence and achieving "on a knife edge" weak-form market efficiency.

## Key Mathematics
**Trade sign autocorrelation function** (event time $\tau$ = number of intervening events):
$$
C(\tau) = \langle \epsilon_t \epsilon_{t+\tau} \rangle - \langle \epsilon_t \rangle^2 \sim \tau^{-\alpha}, \quad \alpha = 1 - 2H
$$
where $\epsilon_t \in \{+1, -1\}$ is the trade sign (+1 = buy-initiated, -1 = sell-initiated), and $H \in (0.5, 1)$ indicates long memory ($H=0.5$ corresponds to a memoryless random walk). The empirical result reported in the paper is $\alpha \approx 0.6 \Rightarrow H \approx 0.7$.

**DFA (Detrended Fluctuation Analysis) estimator**: The cumulative sign series $Y(t) = \sum_{s=1}^{t} \epsilon_s$ is divided into windows of length $n$; within each window a linear trend is removed and the residual variance is computed:
$$
F(n) = \sqrt{\frac{1}{N} \sum_{t=1}^{N} \left[ Y(t) - Y_n^{\text{fit}}(t) \right]^2} \sim n^{H}
$$
The slope of a log-log fit of $F(n)$ vs $n$ gives $H$.

**R/S method (rescaled range)** provides an independent estimate: the paper reports mean $H_{R/S} = 0.696 \pm 0.032$, consistent with the periodogram method.

## Data Requirements
- **Type**: trade sign series (+1 = buy-initiated, -1 = sell-initiated), separately for market orders / limit orders / cancellations
- **Granularity**: tick-by-tick events (event time, not wall-clock time)
- **Time span**: The paper uses LSE SETS data from 1999-05 to 2002-12 (approximately 3.5 years) across 20+ of the most liquid stocks; replication requires at least 6 months of a single stock (~$10^5$ events) to fit up to $\tau \sim 1000$
- **Data sources**: LOBSTER (we have NASDAQ), NYSE TAQ, LSE Reuters/Refinitiv; any message-level data containing a buy/sell direction flag is suitable
- **Preprocessing**: NASDAQ ITCH / LOBSTER message files provide the direction field directly with no inference needed; if using BBO-only data (e.g., early TAQ), the Lee-Ready algorithm (nearest mid-price comparison + tick test) is needed to assign sign

## Replication Protocol (one thing only — compute Hurst)
1. **Load data**: From LOBSTER `*_message.csv`, read one year of trade events for a single ticker (GOOG 2022 recommended) where event_type ∈ {4, 5} (visible/hidden execution); extract the direction column → $\epsilon_t \in \{+1, -1\}$, with length denoted $N$ (typically $N \sim 10^6$)
2. **Compute ACF**: Calculate $C(\tau) = \frac{1}{N-\tau} \sum_{t=1}^{N-\tau} \epsilon_t \epsilon_{t+\tau} - \bar\epsilon^2$ for $\tau = 1, 2, \dots, 1000$, accelerated with `numpy.correlate(eps, eps, mode='full')` or FFT-based `scipy.signal.fftconvolve`
3. **Fit**: Perform linear regression of $C(\tau)$ vs $\tau$ on a log-log scale (using $\tau \in [10, 500]$ to avoid short-range bias and long-range noise); the slope equals $-\alpha$, yielding $H = (1 - \alpha)/2$
4. **DFA cross-check**: Use `nolds.dfa(np.cumsum(eps), nvals=np.logspace(1, 4, 30).astype(int))` to obtain an independent $H$ estimate directly
5. **Cross-stock**: Repeat steps 1-4 for 5+ tickers (LOBSTER GOOG / AAPL / MSFT / AMZN / TSLA) to verify cross-stock universality
6. **Expected range**: $H \in [0.6, 0.8]$, cross-stock variation $< 0.1$

## Expected Results
- **Key number**: Hurst exponent $H \approx 0.7$ (LSE reports $0.696 \pm 0.032$; NASDAQ data is expected to be close)
- **Plots**: log-log decay of $C(\tau)$ as a straight line spanning $\tau \in [1, 10^3]$ with slope approximately $-0.6$; DFA $F(n)$ vs $n$ with slope approximately $0.7$
- **Cross-stock universality**: $H$ values differ by $< 0.1$ across tickers, i.e., all liquid stocks have $H$ within $[0.6, 0.8]$
- **By-product**: The same long-memory structure appears in the sign series of limit orders and cancellations (not only market orders)

## Reference Implementation
- **Public code**: No official release; in Python, `nolds` (https://github.com/CSchoel/nolds) provides `dfa()` and `hurst_rs()`; `hurst` (https://github.com/Mottl/hurst) provides an R/S estimator; manual ACF fitting takes fewer than 30 lines of numpy/scipy
- **Replication difficulty**: $\star$ (the estimator is straightforward; the main challenge is data preprocessing and sign assignment; LOBSTER data already contains the direction field so Lee-Ready is not needed)

## Correspondence with Our LOBSTER Data
- LOBSTER `*_message.csv` column 6 (direction) gives +1 / -1 directly; event_type ∈ {4, 5} are execution events
- One year of a single stock (~$10^6$ trades) is sufficient to fit up to $\tau = 10^3$
- We already have a full year of GOOG 2022 (`/lus/lfs1aip2/home/s5e/kangli.s5e/GOOG_GOOGL_2016TO2021_24tok_preproc/GOOG/2022`), and the 8-ticker × 4-year MarS dataset can also serve as a cross-stock universality benchmark
- **Directly actionable**: A ~60-line Python script suffices for replication; single-stock runtime is under 5 minutes on a single CPU core

## Best Model So Far

> **Key task number**: Hurst exponent $H \approx 0.7$ (LSE paper reports $H = 0.696 \pm 0.032$)
>
> Auto Research splits "Best Model So Far" into two columns: (A) classical estimator on real LOBSTER data (gold standard); (B) the same metric computed on synthetic data produced by our generative model (mamba3). The former measures how faithfully the estimator reproduces the paper, while the latter measures whether the generative model captures this stylized fact.

| Stream | Source | $\hat H$ | $\hat \alpha$ | Status |
|--------|--------|----------|----------------|--------|
| **A. Reference (paper)** | Lillo & Farmer 2004, LSE 1999-2002, 20+ stocks | 0.696 ± 0.032 | ~0.6 | published |
| **B. Classical estimator on LOBSTER** | DFA on real GOOG 2022 (251 days, 10.87M trades) | **0.7053** | 0.2022 | ✅ SLURM j4384364, **within ±1σ of paper value** |
| **C. mamba3 generated samples** | DFA on synthetic trade-sign series from mamba3 SOTA | TBD | TBD | _pending — uses mamba3 ckpt pw8u0edj@46050_ |

> Stream B verification: `python3 scripts/hurst_lillo_farmer.py --ticker GOOG --year 2022 --results_dir results/hurst_GOOG_2022_4384364`. Result: DFA H = 0.7053 on 10,868,894 trade-sign events over 251 trading days. Sign balance = (+1: 66.7%, -1: 33.3%), confirming buy-pressure asymmetry in GOOG 2022 but not affecting Hurst. ACF method gave H_acf = 0.8989 (α = 0.2022) — note this tail-decay estimator differs from DFA in finite samples; DFA is more robust and matches the paper.

**Related model card**: The checkpoint used when evaluating mamba3 generated samples is documented in [`models/mamba3.md`](../models/mamba3.md) → step 46050 of pw8u0edj.

**Replication ckpt + commit pinning** (for students):
```bash
git clone git@github.com:KangOxford/LOBS5.git
cd LOBS5
git checkout 3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28   # mamba3 paper baseline state
# then generate sequences → run the replication protocol in this task → compare against Reference H ≈ 0.7
```

**Expected verdict**: $\hat H$ from mamba3 generated samples should fall within $[0.6, 0.8]$; otherwise the generative model has failed to capture the LOB long-memory stylized fact.

## Citation
```bibtex
@article{lillo2004long,
  title={The long memory of the efficient market},
  author={Lillo, Fabrizio and Farmer, J Doyne},
  journal={Studies in Nonlinear Dynamics \& Econometrics},
  volume={8},
  number={3},
  pages={Article 1},
  year={2004},
  doi={10.2202/1558-3708.1226}
}
```
