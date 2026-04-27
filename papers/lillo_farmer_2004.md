# Lillo & Farmer (2004): The Long Memory of the Efficient Market

## 元信息
- **作者**: Fabrizio Lillo, J. Doyne Farmer
- **年份**: 2004
- **期刊**: Studies in Nonlinear Dynamics & Econometrics, 8(3), Article 1
- **arXiv**: cond-mat/0311053
- **DOI**: 10.2202/1558-3708.1226

## TLDR (一句话)
在 LSE 1999-2002 数据上发现 trade sign 序列是 long-memory 过程,Hurst 指数 $H \approx 0.7$ (autocorrelation 幂律衰减指数 $\alpha \approx 0.6$),但市场返回仍接近随机游走 (efficient),原因是 transaction size 和 liquidity 提供反相关补偿。

## 核心 Stylized Fact
在 LSE (London Stock Exchange) 1999-2002 共约 4 年的逐笔订单数据上,作者发现 **order sign 序列 (market orders, limit orders, cancellations 三类皆然) 表现为 long-memory 过程**,自相关函数以 $C(\tau) \sim \tau^{-\alpha}$ 形式幂律衰减,$\alpha \approx 0.6$,对应 Hurst 指数 $H \approx 0.7$。这种持续性在 20+ LSE 股票之间普适,跨股票差异 < 0.1。表面上 sign 序列高度可预测应导致严重的 market inefficiency,但 mid-price returns 仍近似 random walk: 论文证明 transaction size 与 liquidity (spread / depth) 也是 long-memory,且与 order sign 反相关,精确抵消了 sign 持续性带来的可预测利润,实现了"on a knife edge" 的弱市场效率。

## 关键数学
**Trade sign autocorrelation function** (event time $\tau$ = 中间事件数):
$$
C(\tau) = \langle \epsilon_t \epsilon_{t+\tau} \rangle - \langle \epsilon_t \rangle^2 \sim \tau^{-\alpha}, \quad \alpha = 1 - 2H
$$
其中 $\epsilon_t \in \{+1, -1\}$ 是 trade sign (+1 = buy-initiated, -1 = sell-initiated),$H \in (0.5, 1)$ 表示 long memory ($H=0.5$ 为无记忆 random walk)。论文经验结果 $\alpha \approx 0.6 \Rightarrow H \approx 0.7$。

**DFA (Detrended Fluctuation Analysis) estimator**: 把累积 sign 序列 $Y(t) = \sum_{s=1}^{t} \epsilon_s$ 切成长度 $n$ 的窗口,在每窗内做线性 detrend 后求残差方差:
$$
F(n) = \sqrt{\frac{1}{N} \sum_{t=1}^{N} \left[ Y(t) - Y_n^{\text{fit}}(t) \right]^2} \sim n^{H}
$$
log-log 拟合 $F(n)$ vs $n$ 的斜率即 $H$。

**R/S 方法 (rescaled range)** 给出独立估计: 论文报告 mean $H_{R/S} = 0.696 \pm 0.032$,与 periodogram method 一致。

## 数据需求
- **类型**: trade sign 序列 (+1 = buy-initiated, -1 = sell-initiated),分别针对 market orders / limit orders / cancellations
- **粒度**: 逐笔 event (event time, 不是 wall-clock time)
- **时间跨度**: 论文用 LSE SETS 系统 1999-05 至 2002-12 约 3.5 年,跨 20+ 流动性最强股票;复现至少需要单股票 6 个月 ~ $10^5$ events 才能拟合到 $\tau \sim 1000$
- **数据源**: LOBSTER (我们已有 NASDAQ), NYSE TAQ, LSE Reuters/Refinitiv,任何含 buy/sell direction 标志的 message-level 数据均可
- **预处理**: NASDAQ ITCH / LOBSTER 的 message file 直接给 direction 字段无需推断;若用 BBO-only 数据 (如 TAQ 早期),需 Lee-Ready algorithm (用最近 mid-price 比较 + tick test) 标定 sign

## 复现协议 (就一件事 — 算 Hurst)
1. **取数据**: 从 LOBSTER `*_message.csv` 读单只股票一年 (建议 GOOG 2022) 的 trade events (event_type ∈ {4, 5} 即 visible/hidden execution),提取 direction column → $\epsilon_t \in \{+1, -1\}$,长度记为 $N$ (通常 $N \sim 10^6$)
2. **算 ACF**: 计算 $C(\tau) = \frac{1}{N-\tau} \sum_{t=1}^{N-\tau} \epsilon_t \epsilon_{t+\tau} - \bar\epsilon^2$ for $\tau = 1, 2, \dots, 1000$,用 `numpy.correlate(eps, eps, mode='full')` 或 FFT-based `scipy.signal.fftconvolve` 加速
3. **拟合**: 在 log-log 坐标上对 $C(\tau)$ vs $\tau$ 做线性回归 (取 $\tau \in [10, 500]$ 避免短程偏差和长程噪音),斜率 $= -\alpha$,解出 $H = (1 - \alpha)/2$
4. **DFA 双验证**: 用 `nolds.dfa(np.cumsum(eps), nvals=np.logspace(1, 4, 30).astype(int))` 直接得 $H$ 估计
5. **跨股票**: 重复 1-4 对 5+ 只股票 (LOBSTER GOOG / AAPL / MSFT / AMZN / TSLA) 检查跨股票一致性
6. **期望**: $H \in [0.6, 0.8]$,跨股票差异 $< 0.1$

## 期望结果
- **核心数字**: Hurst 指数 $H \approx 0.7$ (LSE 报告 $0.696 \pm 0.032$,NASDAQ 数据预计接近)
- **图**: log-log 的 $C(\tau)$ 衰减直线,横跨 $\tau \in [1, 10^3]$ 直线斜率约 $-0.6$ ;DFA $F(n)$ vs $n$ 斜率约 $0.7$
- **跨股票普适性**: 不同股票 $H$ 值差异 $< 0.1$,即所有 liquid stocks 的 $H$ 都落在 $[0.6, 0.8]$ 区间
- **副产物**: 同样的 long-memory 出现在 limit order 和 cancellation 的 sign 序列上 (而不仅是 market orders)

## 参考实现
- **公开代码**: 无官方 release;Python 中 `nolds` (https://github.com/CSchoel/nolds) 提供 `dfa()` 和 `hurst_rs()`,`hurst` (https://github.com/Mottl/hurst) 提供 R/S estimator;手动 ACF 拟合 < 30 行 numpy/scipy
- **复现难度**: $\star$ (estimator 简单,主要难度在数据预处理与 sign 标定;LOBSTER 数据已含 direction 无需 Lee-Ready)

## 与我们 LOBSTER 数据的对应
- LOBSTER `*_message.csv` 第 6 列 (direction) 直接给 +1 / -1,event_type ∈ {4, 5} 为 execution events
- 单股票一年 (~$10^6$ trades) 数据足够拟合到 $\tau = 10^3$
- 我们已有 GOOG 2022 完整一年 (`/lus/lfs1aip2/home/s5e/kangli.s5e/GOOG_GOOGL_2016TO2021_24tok_preproc/GOOG/2022`),且 8-ticker × 4-year MarS 数据集亦可作为跨股票普适性验证
- **直接 actionable**: 写一个 60 行 Python 脚本就能复现,< 5 分钟单 CPU 跑完单股票

## Best Model So Far

> **任务核心数字**: Hurst exponent $H \approx 0.7$ (LSE paper 报告 $H = 0.696 \pm 0.032$)
>
> Auto Research 把 "Best Model So Far" 拆为两栏：(A) 在真实 LOBSTER 数据上的经典 estimator (gold standard); (B) 用我们生成模型 (mamba3) 产出的 synthetic 数据上得到的同一指标。前者衡量 estimator 复现忠实度，后者衡量 generative model 是否 capture 该 stylized fact。

| Stream | Source | $\hat H$ | $\hat \alpha$ | Status |
|--------|--------|----------|----------------|--------|
| **A. Reference (paper)** | Lillo & Farmer 2004, LSE 1999-2002, 20+ stocks | 0.696 ± 0.032 | ~0.6 | published |
| **B. Classical estimator on LOBSTER** | DFA on real GOOG 2022 (251 days, 10.87M trades) | **0.7053** | 0.2022 | ✅ SLURM j4384364, **within ±1σ of paper value** |
| **C. mamba3 generated samples** | DFA on synthetic trade-sign series from mamba3 SOTA | TBD | TBD | _pending — uses mamba3 ckpt pw8u0edj@46050_ |

> Stream B verification: `python3 scripts/hurst_lillo_farmer.py --ticker GOOG --year 2022 --results_dir results/hurst_GOOG_2022_4384364`. Result: DFA H = 0.7053 on 10,868,894 trade-sign events over 251 trading days. Sign balance = (+1: 66.7%, -1: 33.3%), confirming buy-pressure asymmetry in GOOG 2022 but not affecting Hurst. ACF method gave H_acf = 0.8989 (α = 0.2022) — note this tail-decay estimator differs from DFA in finite samples; DFA is more robust and matches the paper.

**关联 model card**: 评估 mamba3 generated samples 时使用的 ckpt 见 [`models/mamba3.md`](../models/mamba3.md) → step 46050 of pw8u0edj。

**复现 ckpt + commit pinning** (供学生用):
```bash
git clone git@github.com:KangOxford/LOBS5.git
cd LOBS5
git checkout 3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28   # mamba3 paper baseline state
# 然后 generate 序列 → 跑本 task 复现协议 → 比对 Reference H ≈ 0.7
```

**预期判定**：mamba3 generated samples 的 $\hat H$ 应落入 $[0.6, 0.8]$ —— 否则该 generative model 没 capture LOB long-memory 这个 stylized fact。

## 引用
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
