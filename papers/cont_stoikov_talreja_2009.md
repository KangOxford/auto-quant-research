# Cont, Stoikov, Talreja (2009): A Stochastic Model for Order Book Dynamics

## 元信息
- **作者**: Rama Cont, Sasha Stoikov, Rishi Talreja
- **年份**: 2009 (publ. 2010 in Operations Research)
- **期刊**: Operations Research, 58(3), 549-563
- **arXiv**: SSRN 1273160 (preprint, Sep 2008); 论文 DOI 10.1287/opre.1090.0780
- **机构**: Columbia University (IEOR)

## TLDR (一句话)
LOB 在每个 price level 可建模为独立 birth-death 队列, limit order 到达强度沿距 best quote 的距离按 power law $\lambda(i) = k / i^{\alpha}$ 衰减, cancellation 强度与 queue size 严格成正比 ($\theta(i) \cdot n$), market order 到达近似 Poisson, 三类 event rate 都可从 Level II 高频数据 closed-form 估计。

## 核心 Stylized Fact
基于 Tokyo Stock Exchange Level II 数据, 论文给出 LOB queue dynamics 的三个 empirical regularities: (1) **limit order 到达强度** 在距 opposite-side best quote 的 $i$ 个 tick 处, 按 power law $\lambda(i) = k / i^{\alpha}$ 衰减, 实证 $\alpha$ 在 0.5 量级 (Sky Perfect Communications $\alpha = 0.52$), Bouchaud et al. 在其它市场报告 $\alpha \in [1.5, 2.5]$; (2) **cancellation 强度** 与该 level 的 queue size 严格成正比, $\theta_{\text{total}}(i, n) = \theta(i) \cdot n$, 即每个挂单独立 cancel 且 hazard rate 常数 $\theta(i)$, 数值上 $\theta(i)$ 也随 $i$ 缓慢下降; (3) **market order** 到达近似为常数强度 Poisson 过程, 速率 $\mu$ (Sky Perfect $\mu = 0.94$ 单位 limit order size / 分钟)。三者相加构成一个 birth-death 队列, best quote 的变化时刻就是该队列的 first-passage time。

## 关键数学

**Limit order arrival intensity** (距 opposite-side best 的 $i$ 个 tick):
$$
\lambda(i) = \frac{k}{i^{\alpha}}
$$

实证 (least-squares fit on $i = 1,\dots,5$):
$$
\min_{k, \alpha} \; \sum_{i=1}^{5} \left( \hat{\lambda}(i) - \frac{k}{i^{\alpha}} \right)^{2}
$$
Sky Perfect Communications: $k = 1.92$, $\alpha = 0.52$ (单位: limit-order-size 块 / 分钟). 跨市场 Bouchaud–Zovko–Farmer 等研究报告 $\alpha \in [1.5, 2.5]$。

**Cancellation rate** (level $i$ 当前 queue size 为 $x$ 时):
$$
\theta_{\text{total}}(i, x) = \theta(i) \cdot x
$$
即假设每个挂单独立地以 hazard rate $\theta(i)$ cancel, batch 总 cancel 强度线性。estimator:
$$
\hat{\theta}(i) = \frac{N_{c}(i)}{T \cdot Q_{i}}
$$
其中 $N_c(i)$ 为距 best $i$ 个 tick 处的总 cancel 次数, $Q_i$ 为该 level 的稳态平均 queue size。

**Market order arrival**: 双边独立 Poisson, 速率 $\mu$:
$$
\hat{\mu} = \frac{N_{m}}{T} \cdot \frac{S_{m}}{S_{l}}
$$
($S_m, S_l$ 分别为市价单/限价单平均 size, 用以将 market order 计数换算成 limit-order-size 单位)。

**Best price 变化的概率** = birth-death first-passage 概率: 给定当前 queue size, 计算 queue 耗尽 (best price move 一格) 的概率, 文中通过 Laplace transform 给出 closed form, 不需要 Monte Carlo。

**Sky Perfect Communications 完整 Table 2 估计** (单位 limit-order-size 块 / 分钟):

| $i$ | $\hat{\lambda}(i)$ | $\hat{\theta}(i)$ |
|-----|---------------------|---------------------|
| 1   | 1.85                | 0.71                |
| 2   | 1.51                | 0.81                |
| 3   | 1.09                | 0.68                |
| 4   | 0.88                | 0.56                |
| 5   | 0.77                | 0.47                |

$\hat{\mu} = 0.94$, $k = 1.92$, $\alpha = 0.52$。

## 数据需求
- **类型**: Level II LOB 数据 (best 5 levels each side), 包含 trades + quotes 时间戳
- **粒度**: event-by-event (quote 变化和 trade 时间戳精确到秒级)
- **时间跨度**: 论文用 Tokyo Stock Exchange 上 (具体未量化, 长度记为 $T$ 分钟); 主表展示 Sky Perfect Communications 单只股票
- **数据源**: Tokyo Stock Exchange Level II (论文原数据); LOBSTER (Nasdaq, 完美匹配, message file 直接区分 4 种 event type), Nasdaq ITCH, NYSE OpenBook 都可
- **关键字段**: event type (limit submission / cancellation / market order), price level (距 best 的 tick 数), size, side, timestamp

## 复现协议 (就两件事 — fit 三个 rate)
1. 从 LOBSTER message file 按 event type 分组, 计算 $S_m, S_l, S_c$ 三类事件的平均 size, 选 $S_l$ 作为 size 单位 (一个 size-$S_l$ 的 block 算一个 event)
2. **Limit arrival rate** $\lambda(i)$:
   - 对每个 distance $i = 1, 2, \dots, 10$ (距 opposite-side best 的 tick 数), 算 $\hat{\lambda}(i) = N_l(i) / T$ (单位时间 limit 数量, 距离 $i$ 处)
   - 在 $i = 1,\dots,5$ 上做 log-log least-squares fit, 求 $k, \alpha$
   - 验证: $\log \hat{\lambda}(i)$ vs $\log i$ 应落在直线上
3. **Cancellation rate** $\theta(i)$:
   - 先估稳态 queue size $Q_i$ (Level II 各 quote row 的 size 平均, 除以 $S_l$)
   - $\hat{\theta}(i) = N_c(i) / (T \cdot Q_i)$ — 即 cancel 频率除以 queue 大小, 直接得到每挂单 hazard rate
   - 验证 linearity: 把 cancel count 在不同 $Q$ bin 上 plot, 应落在过原点直线
4. **Market order rate** $\mu$:
   - $\hat{\mu} = (N_m / T) \cdot (S_m / S_l)$ (将 market order 用 limit size 单位 normalize)
   - 验证 Poisson 性: 检查 inter-arrival time 是否近似 exponential 分布
5. 用 fit 出的 $(\lambda, \mu, \theta)$ 模拟 birth-death queue, 用 Laplace transform (论文 Section 4) 计算 best-price first-passage 分布, 与实际 LOB best-quote 变化时间分布对比

## 期望结果
- **核心数字** (复现 Sky Perfect 量级):
  - $\alpha \in [0.5, 2.5]$ (limit arrival decay exponent, 跨股票/市场差异大; Sky Perfect 0.52, Zovko-Farmer/Bouchaud 1.5–2.5)
  - $\mu \approx O(\text{1 / 分钟})$ for liquid stocks (Sky Perfect 0.94)
  - $\theta(i) \approx 0.4 - 0.8$ per limit-order-size 块 / 分钟 (Sky Perfect 0.47–0.81), per-ticker stable
- **图**:
  - $\log \hat{\lambda}(i)$ vs $\log i$ — 接近直线 (Figure 1a, 距 1–10 ticks)
  - $\hat{\theta}(i) \cdot Q_i$ (i.e. observed cancel rate) vs queue size — 应过原点直线
  - market order inter-arrival CDF — exponential (Poisson 检验)

## 参考实现
- **公开代码**: 论文本身无开源代码; 可参考 ABIDES (agent-based interactive discrete event simulator, Byrd et al. 2020) 中的 stochastic LOB module, 以及 mlofi / lob_inference 类教学库
- **复现难度**: ⭐⭐ (estimator 都是单变量统计, 唯一难点是从 raw message file 正确切分 event type 和 distance-to-best)
- **数据可得性**: 高 (LOBSTER 直接给, 我们已有 8 ticker × 4 年)

## 与我们 LOBSTER 数据的对应
- **LOBSTER message file event type**:
  - 1 = new limit order submission → 入 $N_l(i)$
  - 2 = partial cancellation → 入 $N_c(i)$ (按 cancel size / $S_l$ 折算)
  - 3 = full cancellation/deletion → 入 $N_c(i)$
  - 4 = visible execution (market order) → 入 $N_m$
  - 5 = hidden execution → 论文明确忽略 (hidden / iceberg 不影响 best quote)
- 完美对应论文的 limit / cancel / market 三类 event
- distance to best 直接从 message price - best bid/ask 除以 tick size 算
- **直接 actionable**: 单股一日 (~5e5 events) ≈ 数分钟 Python pandas 实现完整 estimator, 我们 4 年 × 8 ticker 数据足够交叉验证 $\alpha, \mu, \theta$ 的稳定性

## Best Model So Far

> **任务核心数字**: 三个 rate $(\lambda, \mu, \theta)$ 的实证估计 + power-law decay $\alpha$
>
> Auto Research 三栏 (paper / classical / mamba3-generated)：

| Stream | Source | $\hat \alpha$ | $\hat \mu$ | $\hat \theta(i=1)$ | Status |
|--------|--------|---------------|------------|---------------------|--------|
| **A. Reference (paper)** | Sky Perfect Communications, TSE Level II | 0.52 | 0.94 | 0.71 | published |
| **B. Classical estimator on LOBSTER** | 8 tickers × 4 yr, event-type 拆分 + log-log fit + cancel hazard | TBD | TBD | TBD | _pending — 单股一日 ~5e5 events，几分钟 Python 跑完_ |
| **C. mamba3 generated samples** | 同 estimator 在 mamba3 SOTA generated message stream 上 | TBD | TBD | TBD | _pending — uses mamba3 ckpt pw8u0edj@46050_ |

**关联 model card**: 评估 mamba3 generated samples 用的 ckpt 见 [`models/mamba3.md`](../models/mamba3.md) → step 46050 of pw8u0edj。

**复现 ckpt + commit pinning**:
```bash
git clone git@github.com:KangOxford/LOBS5.git
cd LOBS5
git checkout 3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28   # mamba3 paper baseline state
# generate per-ticker per-day message stream → 按 event_type ∈ {1,2,3,4,5} 分组 → fit 三个 rate
```

**预期判定**：
- Stream B (real LOBSTER): $\hat \alpha \in [0.5, 2.5]$（跨股票/市场差异大），$\hat \mu \sim 1$/min, $\hat \theta(1) \in [0.4, 0.8]$ ✓
- Stream C (mamba3): 三个 rate 应与 Stream B 在**同 ticker 同日**对比时数值接近 → mamba3 capture 了 birth-death queue dynamics;
  否则 generative model 对 limit/cancel/market 三类事件的相对频率失真

## 引用
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
