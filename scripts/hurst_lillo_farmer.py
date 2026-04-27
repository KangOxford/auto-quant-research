#!/usr/bin/env python3
"""Compute Hurst exponent of trade-sign series (Lillo & Farmer 2004 stylized fact).

Input:  raw LOBSTER .7z archives at /lus/.../quant/lobster/<year>/<YYYYMMDD>/<TICKER>.7z
Output: H estimate via DFA + R/S, ACF log-log plot, saved to RESULTS_DIR.

Usage (CLI):
  python3 hurst_lillo_farmer.py \
      --ticker GOOG \
      --year 2022 \
      --results_dir /lus/.../auto_research/results/hurst_goog_2022
"""
from __future__ import annotations
import argparse, glob, os, sys, json, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import py7zr


def extract_one_day(arc_path: str, work_dir: str) -> list[str]:
    """Extract message.csv files from one day's .7z archive."""
    out = []
    with py7zr.SevenZipFile(arc_path, mode='r') as z:
        msg_files = [n for n in z.getnames() if 'message' in n.lower() and n.endswith('.csv')]
        z.extract(targets=msg_files, path=work_dir)
        for m in msg_files:
            out.append(str(Path(work_dir) / m))
    return out


def trade_signs_from_csv(csv_path: str) -> np.ndarray:
    """Read LOBSTER message.csv, filter event_type∈{4,5}, return direction series."""
    df = pd.read_csv(csv_path, header=None,
                     names=['time','event_type','order_id','size','price','direction','aux'])
    trades = df[df['event_type'].isin([4, 5])]
    return trades['direction'].astype(np.int8).values


def compute_acf(eps: np.ndarray, max_lag: int = 1000) -> tuple[np.ndarray, np.ndarray]:
    """Compute autocorrelation up to max_lag using FFT."""
    n = len(eps)
    eps_c = eps.astype(np.float64) - eps.mean()
    var = (eps_c ** 2).mean()
    fft = np.fft.fft(eps_c, n=2 * n)
    acf_full = np.real(np.fft.ifft(fft * np.conj(fft)))[:max_lag + 1]
    norm = np.arange(n, n - max_lag - 1, -1)
    acf = acf_full / (norm * var)
    lags = np.arange(max_lag + 1)
    return lags[1:], acf[1:]


def fit_alpha(lags: np.ndarray, acf: np.ndarray, fit_range=(10, 500)) -> tuple[float, float]:
    """Fit C(τ) ~ τ^(-α) via log-log OLS in fit_range."""
    mask = (lags >= fit_range[0]) & (lags <= fit_range[1]) & (acf > 0)
    if mask.sum() < 5:
        return float('nan'), float('nan')
    log_l = np.log(lags[mask])
    log_c = np.log(acf[mask])
    slope, intercept = np.polyfit(log_l, log_c, 1)
    alpha = -slope
    return alpha, intercept


def dfa_hurst(eps: np.ndarray, n_min=10, n_max=10000, n_points=30) -> tuple[float, np.ndarray, np.ndarray]:
    """Detrended Fluctuation Analysis: F(n) ~ n^H."""
    Y = np.cumsum(eps - eps.mean())
    ns = np.unique(np.logspace(np.log10(n_min), np.log10(min(n_max, len(Y) // 4)), n_points).astype(int))
    fs = []
    for n in ns:
        n_segments = len(Y) // n
        if n_segments < 2: continue
        F2 = 0
        for i in range(n_segments):
            seg = Y[i * n:(i + 1) * n]
            t = np.arange(n)
            slope, intercept = np.polyfit(t, seg, 1)
            resid = seg - (slope * t + intercept)
            F2 += (resid ** 2).mean()
        fs.append(np.sqrt(F2 / n_segments))
    fs = np.array(fs)
    ns = ns[:len(fs)]
    log_n = np.log(ns)
    log_f = np.log(fs)
    H, _ = np.polyfit(log_n, log_f, 1)
    return float(H), ns, fs


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ticker', default='GOOG')
    p.add_argument('--year', type=int, default=2022)
    p.add_argument('--lobster_root', default='/lus/lfs1aip2/projects/s5e/quant/lobster')
    p.add_argument('--results_dir', required=True)
    p.add_argument('--max_days', type=int, default=None,
                   help='Limit number of days (for smoke testing)')
    p.add_argument('--max_lag', type=int, default=2000)
    args = p.parse_args()

    Path(args.results_dir).mkdir(parents=True, exist_ok=True)
    log = open(Path(args.results_dir) / 'hurst.log', 'w')

    def echo(s):
        print(s); log.write(s + '\n'); log.flush()

    year_root = Path(args.lobster_root) / str(args.year)
    if not year_root.exists():
        echo(f"FATAL: {year_root} not found"); sys.exit(1)
    day_dirs = sorted([d for d in year_root.iterdir() if d.is_dir() and d.name.startswith(str(args.year))])
    if args.max_days:
        day_dirs = day_dirs[:args.max_days]
    echo(f"[setup] ticker={args.ticker} year={args.year} days={len(day_dirs)}")

    # Extract + collect trade signs across all days
    all_signs = []
    work = tempfile.mkdtemp(prefix='lobster_hurst_')
    for i, d in enumerate(day_dirs):
        arc = d / f'{args.ticker}.7z'
        if not arc.exists():
            echo(f"  [{i+1}/{len(day_dirs)}] {d.name}: no {args.ticker}.7z, skip")
            continue
        try:
            files = extract_one_day(str(arc), work)
            for f in files:
                signs = trade_signs_from_csv(f)
                all_signs.append(signs)
                os.unlink(f)
            if (i + 1) % 25 == 0 or i == len(day_dirs) - 1:
                total = sum(len(s) for s in all_signs)
                echo(f"  [{i+1}/{len(day_dirs)}] {d.name}: cumulative trades = {total:,}")
        except Exception as e:
            echo(f"  [{i+1}/{len(day_dirs)}] {d.name}: ERR {e}")

    if not all_signs:
        echo("FATAL: no trade signs collected"); sys.exit(1)

    eps = np.concatenate(all_signs)
    echo(f"\n[data] total trades: {len(eps):,}")
    echo(f"[data] sign balance: +1={np.mean(eps==1):.4f}, -1={np.mean(eps==-1):.4f}")

    # ACF + alpha fit
    echo(f"\n[ACF] computing up to lag={args.max_lag}...")
    lags, acf = compute_acf(eps, max_lag=args.max_lag)
    alpha, intercept = fit_alpha(lags, acf, fit_range=(10, 500))
    # ACF decay C(τ) ~ τ^(-α), with α = 2 - 2H ⇒ H = 1 - α/2 (standard FBM result)
    H_acf = 1.0 - alpha / 2.0 if not np.isnan(alpha) else float('nan')
    echo(f"[ACF] alpha = {alpha:.4f} (fit τ ∈ [10, 500])")
    echo(f"[ACF] H_acf = 1 - α/2 = {H_acf:.4f}  (paper says ~0.7)")

    # DFA
    echo(f"\n[DFA] computing...")
    H_dfa, ns, fs = dfa_hurst(eps)
    echo(f"[DFA] H_dfa = {H_dfa:.4f}  (paper says 0.696 ± 0.032)")

    # Save numeric results
    out = {
        'ticker': args.ticker, 'year': args.year,
        'n_days': len(day_dirs), 'n_trades': int(len(eps)),
        'sign_balance_buy': float(np.mean(eps == 1)),
        'alpha_acf_fit': float(alpha) if not np.isnan(alpha) else None,
        'H_from_acf': float(H_acf) if not np.isnan(H_acf) else None,
        'H_from_dfa': float(H_dfa),
        'paper_reference': 'Lillo & Farmer 2004, H ≈ 0.696 ± 0.032 (LSE 1999-2002)',
    }
    with open(Path(args.results_dir) / 'hurst_results.json', 'w') as f:
        json.dump(out, f, indent=2)
    echo(f"\n[save] hurst_results.json + hurst.log → {args.results_dir}")

    # Save raw ACF + DFA arrays for plotting
    np.savez(Path(args.results_dir) / 'hurst_arrays.npz',
             lags=lags, acf=acf, dfa_n=ns, dfa_f=fs)
    echo(f"[save] hurst_arrays.npz")

    # log-log plot
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        axes[0].loglog(lags, np.abs(acf), 'b.-', label='|C(τ)|')
        axes[0].set(xlabel='lag τ', ylabel='|C(τ)|', title=f'{args.ticker} {args.year} trade-sign ACF, α={alpha:.3f}')
        axes[0].legend(); axes[0].grid(True, which='both', ls=':')
        axes[1].loglog(ns, fs, 'r.-', label='F(n)')
        axes[1].set(xlabel='window size n', ylabel='F(n)', title=f'DFA, H={H_dfa:.3f}')
        axes[1].legend(); axes[1].grid(True, which='both', ls=':')
        fig.suptitle(f'Lillo & Farmer 2004 replication on LOBSTER {args.ticker} {args.year}')
        fig.tight_layout()
        fig.savefig(Path(args.results_dir) / 'hurst_plot.png', dpi=120)
        echo(f"[save] hurst_plot.png")
    except Exception as e:
        echo(f"[plot] skipped: {e}")

    echo("\n=== SUMMARY ===")
    echo(f"  Paper:       H ≈ 0.696 ± 0.032 (LSE 1999-2002, 20+ stocks)")
    echo(f"  Our (DFA):   H = {H_dfa:.4f}")
    echo(f"  Our (ACF):   H = {H_acf:.4f} (from α = {alpha:.4f})")
    echo(f"  Verdict:     {'✓ supports long memory' if 0.6 <= H_dfa <= 0.85 else '✗ outside expected range'}")

    log.close()


if __name__ == '__main__':
    main()
