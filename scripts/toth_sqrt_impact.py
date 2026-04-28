#!/usr/bin/env python3
"""Tóth et al. (2011): Anomalous Price Impact and Square-Root Law replication.

Algorithm:
1. Cluster LOBSTER trade events into meta-orders (same-side, gap < 60s).
2. For each meta-order m:
   - Q_m = sum of child trade sizes (shares)
   - I_m = (p_end - p_start) / p_start, signed by side (relative return)
3. Per-day aggregates:
   - V_d = sum of all trade sizes (daily volume, shares)
   - sigma_d = std of intra-day log-returns of mid-trade prices
4. Two regressions:
   (a) Raw log-log: log|I_m| ~ delta * log(Q_m) + const   →   exponent delta
   (b) Normalized: I_m / sigma_d ~ Y * sqrt(Q_m / V_d)    →   universal Y

Expected (Tóth 2011): delta ≈ 0.5, Y ≈ 0.5 (small-tick contracts).
LOBSTER limitations: no broker tag → heuristic clustering. Expected exponent
may be in [0.4, 0.6] due to mis-grouping noise.

Usage:
  python3 toth_sqrt_impact.py --ticker GOOG --year 2022 \
                              --results_dir <abs_path>
"""
from __future__ import annotations
import argparse, glob, os, sys, json, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import py7zr


PRICE_SCALE = 10000.0          # LOBSTER prices are 1/10000 USD
META_GAP_SEC = 60.0            # same-side gap threshold for meta-order cut
MIN_Q_SHARES = 50              # filter tiny meta-orders (noise on I)


def extract_one_day(arc_path: str, work_dir: str) -> list[str]:
    """Extract message.csv files from one day's .7z archive."""
    out = []
    with py7zr.SevenZipFile(arc_path, mode='r') as z:
        msg_files = [n for n in z.getnames() if 'message' in n.lower() and n.endswith('.csv')]
        z.extract(targets=msg_files, path=work_dir)
        for m in msg_files:
            out.append(str(Path(work_dir) / m))
    return out


def metaorders_from_csv(csv_path: str) -> tuple[pd.DataFrame, float, float]:
    """Read LOBSTER message CSV, cluster trades into meta-orders.

    Returns:
        meta_df: one row per meta-order with columns (Q, I_rel, side, t_start, t_end, n_trades)
        sigma_d: intra-day log-return std (per-trade)
        V_d: total daily volume (shares)
    """
    df = pd.read_csv(
        csv_path, header=None,
        names=['time','type','oid','size','price','dir','aux'],
        dtype={'time': 'float64', 'type': 'int8', 'size': 'int32',
               'price': 'int64', 'dir': 'int8'},
    )
    trades = df[df['type'].isin([4, 5])].copy()
    if len(trades) < 100:
        return pd.DataFrame(), np.nan, 0.0

    trades = trades.sort_values('time').reset_index(drop=True)
    trades['price_usd'] = trades['price'] / PRICE_SCALE

    # Daily aggregates (use ALL trades, not just clustered)
    V_d = float(trades['size'].sum())
    log_p = np.log(trades['price_usd'].values)
    log_returns = np.diff(log_p)
    # Daily realized volatility: std(per-trade log return) * sqrt(N_returns)
    # gives the std of cumulative open-to-close log return ≈ daily vol (~ O(1%) for liquid stocks).
    if len(log_returns) > 1:
        sigma_per_trade = float(np.std(log_returns))
        sigma_d = sigma_per_trade * np.sqrt(len(log_returns))
    else:
        sigma_d = np.nan

    # Cluster into meta-orders: gap > META_GAP_SEC OR side flip
    trades['gap'] = trades['time'].diff().fillna(0.0)
    trades['side_change'] = (trades['dir'].shift() != trades['dir']).fillna(True)
    trades['new_meta'] = (trades['gap'] > META_GAP_SEC) | trades['side_change']
    trades['meta_id'] = trades['new_meta'].cumsum()

    grp = trades.groupby('meta_id')
    meta_df = pd.DataFrame({
        'Q': grp['size'].sum(),
        'n_trades': grp['size'].count(),
        'side': grp['dir'].first(),
        't_start': grp['time'].first(),
        't_end': grp['time'].last(),
        'p_start': grp['price_usd'].first(),
        'p_end': grp['price_usd'].last(),
    }).reset_index(drop=True)

    # Signed relative price impact: positive when price moves in side's direction
    meta_df['I_rel'] = meta_df['side'] * (meta_df['p_end'] - meta_df['p_start']) / meta_df['p_start']
    return meta_df, sigma_d, V_d


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ticker', default='GOOG')
    p.add_argument('--year', type=int, default=2022)
    p.add_argument('--lobster_root', default='/lus/lfs1aip2/projects/s5e/quant/lobster')
    p.add_argument('--results_dir', required=True)
    p.add_argument('--max_days', type=int, default=None)
    p.add_argument('--min_q', type=int, default=MIN_Q_SHARES,
                   help='Drop meta-orders with Q < this many shares')
    args = p.parse_args()

    Path(args.results_dir).mkdir(parents=True, exist_ok=True)
    log_f = open(Path(args.results_dir) / 'toth.log', 'w')

    def echo(s):
        print(s); log_f.write(s + '\n'); log_f.flush()

    year_root = Path(args.lobster_root) / str(args.year)
    if not year_root.exists():
        echo(f"FATAL: {year_root} not found"); sys.exit(1)
    day_dirs = sorted([d for d in year_root.iterdir() if d.is_dir() and d.name.startswith(str(args.year))])
    if args.max_days:
        day_dirs = day_dirs[:args.max_days]
    echo(f"[setup] ticker={args.ticker} year={args.year} days={len(day_dirs)} min_q={args.min_q}")

    work = tempfile.mkdtemp(prefix='lobster_toth_')
    all_metas = []
    daily_stats = []

    for i, d in enumerate(day_dirs):
        arc = d / f'{args.ticker}.7z'
        if not arc.exists():
            echo(f"  [{i+1}/{len(day_dirs)}] {d.name}: no {args.ticker}.7z, skip")
            continue
        try:
            files = extract_one_day(str(arc), work)
            for f in files:
                meta_df, sigma_d, V_d = metaorders_from_csv(f)
                if len(meta_df) == 0:
                    os.unlink(f); continue
                meta_df['date'] = d.name
                meta_df['sigma_d'] = sigma_d
                meta_df['V_d'] = V_d
                all_metas.append(meta_df)
                daily_stats.append({
                    'date': d.name, 'n_meta': len(meta_df),
                    'sigma_d': sigma_d, 'V_d': V_d,
                })
                os.unlink(f)
            if (i + 1) % 25 == 0 or i == len(day_dirs) - 1:
                tot = sum(len(m) for m in all_metas)
                echo(f"  [{i+1}/{len(day_dirs)}] {d.name}: cumulative meta-orders = {tot:,}")
        except Exception as e:
            echo(f"  [{i+1}/{len(day_dirs)}] {d.name}: ERR {e}")

    if not all_metas:
        echo("FATAL: no meta-orders collected"); sys.exit(1)

    meta = pd.concat(all_metas, ignore_index=True)
    echo(f"\n[data] total meta-orders pre-filter:  {len(meta):,}")
    meta = meta[meta['Q'] >= args.min_q]
    echo(f"[data] after Q >= {args.min_q} shares:    {len(meta):,}")
    meta = meta[meta['I_rel'].abs() > 0]
    echo(f"[data] after |I| > 0 (drop zero-impact): {len(meta):,}")
    meta = meta[(meta['sigma_d'] > 0) & (meta['V_d'] > 0)]
    echo(f"[data] after sigma_d>0 and V_d>0:        {len(meta):,}")

    Q   = meta['Q'].values.astype(float)
    I   = meta['I_rel'].values
    Vd  = meta['V_d'].values.astype(float)
    sd  = meta['sigma_d'].values
    echo(f"\n[data] Q range:        [{Q.min():.0f}, {Q.max():.0f}], median={np.median(Q):.0f}")
    echo(f"[data] |I| (bps) range: [{1e4*np.abs(I).min():.4f}, {1e4*np.abs(I).max():.2f}], median={1e4*np.median(np.abs(I)):.2f}")
    echo(f"[data] V_d range:      [{Vd.min():.0f}, {Vd.max():.0f}]")
    echo(f"[data] sigma_d range:  [{sd.min():.6f}, {sd.max():.6f}]")

    # ===== (a) Raw log-log fit: log|I| vs log Q =====
    echo("\n[fit-a] Raw log-log: log|I| ~ delta * log(Q) + const")
    logQ = np.log(Q)
    logI = np.log(np.abs(I))
    slope_a, intercept_a = np.polyfit(logQ, logI, 1)
    # Residual SE
    resid_a = logI - (slope_a * logQ + intercept_a)
    se_a = np.std(resid_a, ddof=2) / np.sqrt(np.sum((logQ - logQ.mean())**2))
    echo(f"[fit-a] delta_hat = {slope_a:.4f} (SE {se_a:.4f}, 95% CI [{slope_a-1.96*se_a:.3f}, {slope_a+1.96*se_a:.3f}])")
    echo(f"[fit-a] Paper says delta ~ 0.5 (small-tick), [0.4, 0.6] for noisy heuristic clustering.")

    # ===== (b) Normalized linear fit: I/sigma_d ~ Y * sqrt(Q/V_d) (signed) =====
    echo("\n[fit-b] Normalized: I/sigma ~ Y * sqrt(Q/V) (preserves sign)")
    x = np.sign(I) * np.sqrt(Q / Vd)   # signed sqrt(Q/V)
    y = I / sd                          # signed normalized impact
    slope_b, intercept_b = np.polyfit(x, y, 1)
    resid_b = y - (slope_b * x + intercept_b)
    se_b = np.std(resid_b, ddof=2) / np.sqrt(np.sum((x - x.mean())**2))
    echo(f"[fit-b] Y_hat = {slope_b:.4f} (SE {se_b:.4f}, 95% CI [{slope_b-1.96*se_b:.3f}, {slope_b+1.96*se_b:.3f}])")
    echo(f"[fit-b] Paper says Y ~ 0.5 (universal across asset classes).")

    # Save
    out = {
        'ticker': args.ticker, 'year': args.year,
        'n_days': len(day_dirs),
        'n_meta_pre_filter': int(len(np.concatenate([m['Q'].values for m in all_metas]))),
        'n_meta_used': int(len(meta)),
        'min_q_shares': args.min_q,
        'meta_gap_sec': META_GAP_SEC,
        'delta_hat': float(slope_a),
        'delta_se': float(se_a),
        'delta_ci_low': float(slope_a - 1.96 * se_a),
        'delta_ci_high': float(slope_a + 1.96 * se_a),
        'Y_hat': float(slope_b),
        'Y_se': float(se_b),
        'Y_ci_low': float(slope_b - 1.96 * se_b),
        'Y_ci_high': float(slope_b + 1.96 * se_b),
        'paper_reference': 'Tóth et al. 2011, Phys. Rev. X. Expected delta ~ 0.5, Y ~ 0.5.',
    }
    with open(Path(args.results_dir) / 'toth_results.json', 'w') as fh:
        json.dump(out, fh, indent=2)
    echo(f"\n[save] toth_results.json -> {args.results_dir}")

    np.savez(Path(args.results_dir) / 'toth_arrays.npz',
             logQ=logQ, logI=logI, x_norm=x, y_norm=y,
             Q=Q, I=I, V_d=Vd, sigma_d=sd)
    echo(f"[save] toth_arrays.npz")

    # Plots
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
        # (a) raw log-log
        axes[0].scatter(logQ, logI, s=1.5, alpha=0.15, color='steelblue')
        xx = np.linspace(logQ.min(), logQ.max(), 100)
        axes[0].plot(xx, slope_a * xx + intercept_a, 'r-', lw=2,
                     label=f'fit: slope={slope_a:.3f}')
        axes[0].axline((0, intercept_a), slope=0.5, color='green', ls='--',
                       label='paper: slope=0.5')
        axes[0].set(xlabel='log Q', ylabel='log |I|',
                    title=f'{args.ticker} {args.year}: raw log-log fit  delta={slope_a:.3f}')
        axes[0].legend(); axes[0].grid(True, alpha=0.3)
        # (b) normalized
        axes[1].scatter(x, y, s=1.5, alpha=0.15, color='darkorange')
        xx2 = np.linspace(x.min(), x.max(), 100)
        axes[1].plot(xx2, slope_b * xx2 + intercept_b, 'r-', lw=2,
                     label=f'fit: Y={slope_b:.3f}')
        axes[1].plot(xx2, 0.5 * xx2, 'g--', label='paper: Y=0.5')
        axes[1].set(xlabel='sign(I) * sqrt(Q/V)', ylabel='I / sigma_d',
                    title=f'{args.ticker} {args.year}: normalized fit  Y={slope_b:.3f}')
        axes[1].legend(); axes[1].grid(True, alpha=0.3)
        fig.suptitle(f'Tóth 2011 replication on LOBSTER {args.ticker} {args.year}')
        fig.tight_layout()
        fig.savefig(Path(args.results_dir) / 'toth_plot.png', dpi=120)
        echo(f"[save] toth_plot.png")
    except Exception as e:
        echo(f"[plot] skipped: {e}")

    echo("\n=== SUMMARY ===")
    echo(f"  Paper:       delta ~ 0.5, Y ~ 0.5  (universal across asset classes)")
    echo(f"  Our (a):     delta_hat = {slope_a:.4f}  (SE {se_a:.4f})")
    echo(f"  Our (b):     Y_hat     = {slope_b:.4f}  (SE {se_b:.4f})")
    if 0.4 <= slope_a <= 0.6:
        echo(f"  Verdict:    delta in [0.4, 0.6] = supports sqrt-law")
    else:
        echo(f"  Verdict:    delta outside [0.4, 0.6] - heuristic clustering noise OR market regime change")

    log_f.close()


if __name__ == '__main__':
    main()
