# Toth et al. (2011): Anomalous Price Impact and Square-Root Law

## Metadata
- **Authors**: Bence Toth, Yves Lemperiere, Cyril Deremble, Joachim de Lataillade, Julien Kockelkoren, Jean-Philippe Bouchaud
- **Year**: 2011
- **Journal**: Physical Review X 1, 021006
- **arXiv**: 1105.1694
- **Institution**: Capital Fund Management (CFM), Paris

## TLDR (one sentence)
The permanent price impact of a meta-order is proportional to the square root of its executed size ($I \propto Q^{0.5}$); the exponent $\approx 0.5$ is universal across equities, futures, and asset classes, reflecting a market liquidity regime at a "critical" state (the latent order book has a V-shape near the mid-price that vanishes to zero).

## Core Stylized Fact
When an institutional investor slices a meta-order (parent order) of total size $Q$ and executes it incrementally, the average price drift observed from order start to completion is proportional to $\sqrt{Q}$, not linear (as in Kyle 1985) or any other power law. This relationship is stable across equities, futures, different eras, and different markets; the exponent $\delta \approx 0.5$ is a universal constant. It is termed "anomalous" because standard efficient-market theory predicts linear or logarithmic impact, whereas the sqrt relationship implies the market is in a self-organized criticality state: at the moment a meta-order begins, available liquidity near the mid-price is extremely thin (the V-shaped latent book vanishes at mid), so any nonzero order triggers a nonlinear response. This is the meaning of the "critical nature of liquidity."

## Key Mathematics
**Square-root impact law**:
$$
I(Q) = Y \, \sigma_{\text{daily}} \, \sqrt{\frac{Q}{V_{\text{daily}}}}
$$

Where:
- $I(Q)$: permanent (or peak) price impact caused by a meta-order of size $Q$, typically expressed in bps or absolute price change
- $\sigma_{\text{daily}}$: daily volatility of the asset (or over a recent window)
- $V_{\text{daily}}$: total traded volume for the day
- $Y$: universal constant of order unity; the paper estimates $Y \approx 0.5$
- Key finding: empirical exponent $\delta \approx 0.5$ (small-tick contracts), $\delta \approx 0.6$ (large-tick contracts); the paper normalizes to $0.5$

More generally, the literature writes:
$$
I(Q) \propto \sigma \left(\frac{Q}{V}\right)^{\delta}, \quad \delta \approx 0.5
$$

**Why anomalous**: this contradicts Kyle (1985) permanent linear impact ($I \propto Q$) and also differs from the Grinold-Kahn 3/5 power law (a practical rule of thumb). The sqrt relationship cannot be derived from simple informed-trader equilibrium; it requires the V-shape liquidity assumption of the latent/shadow order book (liquidity vanishes at mid) to explain.

## Data Requirements
- **Type**: meta-order data (each record: parent order ID, side, total size $Q$, start/end timestamps, child order slices)
- **Granularity**: meta-order level, not individual trades
- **Time span**: the paper uses CFM's proprietary execution data spanning multiple years (~5 years), covering ~500,000 trades across various futures contracts
- **Data source**: CFM internal execution logs; the key difficulty is that meta-order tags are typically proprietary to institutional traders
- **Alternative**: use publicly available LOBSTER LOB data to cluster meta-orders by aggregating consecutive same-direction trades via trade-sign sequences and time gaps into proxy meta-orders

## Replication Protocol (the one thing — fitting the exponent)
1. Extract all trade events (message types 4/5) from LOBSTER message data, by ticker × day
2. Apply heuristic meta-order clustering: consecutive same-direction (buy/sell) trades with time gap < 60 seconds (sweep 30s/60s/300s) are treated as a single parent order; direction reversals or long idle gaps break the cluster
3. For each clustered meta-order $i$, compute:
   - $Q_i$ = sum of child trade sizes
   - $I_i$ = change in mid-price from meta-order start to end (signed by side, in units of bps or $\sigma$)
   - $V_d$, $\sigma_d$ estimated from total volume / realized volatility on the trading day containing the meta-order
4. Log-log scatter plot: $\log I_i$ vs $\log Q_i$ (or normalized form $I/\sigma$ vs $\sqrt{Q/V}$)
5. OLS fit $\log I = \alpha + \delta \log Q$, report $\hat{\delta}$ with 95% CI; expected $\hat{\delta} \approx 0.5$
6. (Optional) Fit a linear slope $Y$ in the normalized plane $I/\sigma$ vs $\sqrt{Q/V}$; expected $Y \approx 0.5$
7. (Optional) Bin by ticker / market cap / tick size and check exponent stability across subsets

## Expected Results
- **Core number**: impact exponent $\hat{\delta} \approx 0.5$, with 95% CI expected to cover [0.45, 0.55]
- **Plot**: log-log scatter $\log I$ vs $\log Q$ + OLS fit line + slope annotation $\delta = 0.5 \pm \text{SE}$
- **Normalized plot**: $I/\sigma$ vs $\sqrt{Q/V}$ should be approximately linear with slope $Y \approx 0.5$
- **Cross-stock stability**: $\delta$ estimates for large-cap (AAPL, MSFT) / mid- and small-cap / ETFs should be mutually consistent (differences < 0.1)

## Reference Implementation
- **Public code**: no official CFM replication package; subsequent papers by Bouchaud, Donier, and Bonart provide methodological descriptions; general-purpose LOB libraries such as `mfit` / `pylob` in Python can serve as scaffolding, but no turnkey impact-law package exists. Market microstructure courses (e.g., Baruch MFE) have pedagogical notebooks.
- **Replication difficulty**: ⭐⭐⭐ (the challenge is not the regression algorithm itself, but the heuristic choices for meta-order reconstruction and noise control)
- **Data availability**: medium (LOBSTER can proxy; true CFM meta-order tags are unavailable; see Sato & Kanazawa 2024 for a strict universality replication using complete broker-tagged Tokyo Stock Exchange data)

## Correspondence to Our LOBSTER Data
- LOBSTER has no broker / parent-order tags; heuristic clustering is mandatory
- Simplified replication: aggregate consecutive trades sharing the same ticker, side, and time gap < 60s into proxy meta-orders
- Limitation: heuristic reconstruction introduces mis-grouping noise; the empirical exponent may deviate from 0.5 (the empirical range 0.4–0.6 is still considered consistent with the sqrt law); aggressive vs passive trade splits also affect results
- Recommendation: start with a sanity check on a single ticker for a single day, then expand to the full dataset; report a sensitivity analysis over the heuristic parameters

## Best Model So Far

> **Key task numbers**: impact exponent $\delta \approx 0.5$, normalized slope $Y \approx 0.5$
>
> Auto Research three columns (paper / classical / mamba3-generated):

| Stream | Source | $\hat \delta$ | $\hat Y$ | Status |
|--------|--------|---------------|----------|--------|
| **A. Reference (paper)** | Toth et al. 2011, CFM proprietary, multi-asset | 0.5 (small-tick) / 0.6 (large-tick) | ~0.5 | published |
| **B. Classical estimator on LOBSTER** | Heuristic meta-order cluster + log-log OLS on 8 tickers × 4 yr | TBD | TBD | _pending — see replication protocol; empirical range 0.4-0.6 is considered consistent with sqrt law_ |
| **C. mamba3 generated samples** | Same heuristic on synthetic trade stream from mamba3 SOTA | TBD | TBD | _pending — uses mamba3 ckpt pw8u0edj@46050_ |

**Associated model card**: the checkpoint used to evaluate mamba3 generated samples is documented in [`models/mamba3.md`](../models/mamba3.md) → step 46050 of pw8u0edj.

**Replication ckpt + commit pinning**:
```bash
git clone git@github.com:KangOxford/LOBS5.git
cd LOBS5
git checkout 3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28   # mamba3 paper baseline state
# generate full-day continuous trade stream → cluster meta-orders → log-log fit
```

**Expected determination**:
- Stream B (real LOBSTER): $\hat \delta \in [0.4, 0.6]$ ✓
- Stream C (mamba3 generated): $\hat \delta \in [0.4, 0.6]$ → mamba3 has captured the critical liquidity stylized fact;
  otherwise the generative model misrepresents the V-shape assumption of the latent order book

## Citation
```bibtex
@article{toth2011anomalous,
  title={Anomalous price impact and the critical nature of liquidity in financial markets},
  author={Toth, Bence and Lemperiere, Yves and Deremble, Cyril and de Lataillade, Joachim and Kockelkoren, Julien and Bouchaud, Jean-Philippe},
  journal={Physical Review X},
  volume={1},
  number={2},
  pages={021006},
  year={2011}
}
```
