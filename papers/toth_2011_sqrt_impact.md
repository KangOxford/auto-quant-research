# Toth et al. (2011): Anomalous Price Impact and Square-Root Law

## 元信息
- **作者**: Bence Toth, Yves Lemperiere, Cyril Deremble, Joachim de Lataillade, Julien Kockelkoren, Jean-Philippe Bouchaud
- **年份**: 2011
- **期刊**: Physical Review X 1, 021006
- **arXiv**: 1105.1694
- **机构**: Capital Fund Management (CFM), Paris

## TLDR (一句话)
Meta-order 的 permanent price impact 与执行 size 的平方根成正比 ($I \propto Q^{0.5}$), exponent $\approx 0.5$ 跨股票/期货/资产类别普适, 反映市场流动性处于「critical」状态 (latent order book 在 mid-price 附近为 V 形且趋于零)。

## 核心 Stylized Fact
当机构投资者将一个总规模为 $Q$ 的「meta-order」(parent order) 切片后逐步执行, 从下单开始到结束观察到的平均价格漂移与 $\sqrt{Q}$ 成正比, 而不是线性 (Kyle 1985) 或其它 power law。这一关系在跨股票、期货、不同时代、不同市场上保持稳定, exponent $\delta \approx 0.5$ 是一个普适常数。之所以「anomalous」, 是因为标准的有效市场理论预测线性或对数 impact; 而 sqrt 关系暗示市场处于 self-organized criticality 状态: meta-order 启动时 mid-price 附近的可成交流动性极低 (V 形 latent book vanishes at mid), 任意非零订单都触发非线性响应。这就是「critical nature of liquidity」的含义。

## 关键数学
**Square-root impact law**:
$$
I(Q) = Y \, \sigma_{\text{daily}} \, \sqrt{\frac{Q}{V_{\text{daily}}}}
$$

其中:
- $I(Q)$: meta-order size $Q$ 引起的 permanent (或 peak) price impact, 通常以 bps 或绝对价格变化表示
- $\sigma_{\text{daily}}$: 该 asset 当日 (或近期窗口) 的 daily volatility
- $V_{\text{daily}}$: 当日 traded volume
- $Y$: 普适常数, order unity, 论文测得 $Y \approx 0.5$
- 关键: 实证 exponent $\delta \approx 0.5$ (small-tick contracts), $\delta \approx 0.6$ (large-tick contracts), 论文将其归一化到 $0.5$

更一般地, 研究文献写作:
$$
I(Q) \propto \sigma \left(\frac{Q}{V}\right)^{\delta}, \quad \delta \approx 0.5
$$

**为什么 anomalous**: 与 Kyle (1985) permanent linear impact ($I \propto Q$) 矛盾, 也与 Grinold-Kahn 的 3/5 power law (实务 rule of thumb) 不同。Sqrt 关系无法由简单的 informed-trader equilibrium 推出, 必须借助 latent / shadow order book 的 V-shape 流动性假设 (在 mid 处趋于零) 才能解释。

## 数据需求
- **类型**: meta-order 数据 (每条记录: parent order ID, side, total size $Q$, 起止时间, 切片 child orders)
- **粒度**: meta-order level, 不是单 trade
- **时间跨度**: 论文使用 CFM 自有 proprietary execution 数据, 涵盖跨多年 (~5 年级别) 的 ~500,000 笔 trades on 多种 futures contracts
- **数据源**: CFM 内部 execution log, 难点: meta-order tag 通常是机构私有数据
- **替代**: 用 LOBSTER 公开 LOB 数据 cluster meta-order: 把同方向连续 trades 用 trade-sign 序列 + 时间 gap 聚合成 proxy meta-order

## 复现协议(就一件事 — 拟合 exponent)
1. 从 LOBSTER message 数据按 ticker × day 提取所有 trade events (类型 4/5)
2. 用 heuristic cluster meta-order: 同方向 (buy/sell) 连续 trades, 时间 gap < 60 秒 (可 sweep 30s/60s/300s) 视为同一 parent order; 方向反转或长 idle 切断
3. 对每个聚合得到的 meta-order $i$, 计算:
   - $Q_i$ = sum of child trade sizes
   - $I_i$ = mid-price 从 meta-order start 到 end 的变化 (signed by side, 单位 bps 或 $\sigma$)
   - $V_d$, $\sigma_d$ 用 meta-order 所在交易日的 total volume / realized volatility 估计
4. log-log 散点图: $\log I_i$ vs $\log Q_i$ (或归一化形式 $I/\sigma$ vs $\sqrt{Q/V}$)
5. OLS 拟合 $\log I = \alpha + \delta \log Q$, 报告 $\hat{\delta}$ 与 95% CI; 期望 $\hat{\delta} \approx 0.5$
6. (Optional) 在归一化平面 $I/\sigma$ vs $\sqrt{Q/V}$ 上拟合直线斜率 $Y$, 期望 $Y \approx 0.5$
7. (Optional) 按 ticker / market cap / tick size 分桶, 检查 exponent 跨子集稳定性

## 期望结果
- **核心数字**: impact exponent $\hat{\delta} \approx 0.5$, 95% CI 期望覆盖 [0.45, 0.55]
- **图**: log-log 散点 $\log I$ vs $\log Q$ + OLS 拟合直线 + 斜率标注 $\delta = 0.5 \pm \text{SE}$
- **归一化图**: $I/\sigma$ vs $\sqrt{Q/V}$ 应近线性, slope $Y \approx 0.5$
- **跨股票稳定**: 大盘 (AAPL, MSFT) / 中小盘 / ETF 的 $\delta$ 应彼此一致 (差异 < 0.1)

## 参考实现
- **公开代码**: 没有官方 CFM 复现包; 学术界 Bouchaud, Donier, Bonart 后续 paper 提供方法描述; Python 端 `mfit` / `pylob` 等通用 LOB 库可作支架, 无 turnkey impact-law package。市场 microstructure 课程 (e.g., Baruch MFE) 有教学 notebook
- **复现难度**: ⭐⭐⭐ (难点不是回归算法, 是 meta-order 重建的 heuristic 选择和 noise 控制)
- **数据可得性**: 中 (LOBSTER 能 proxy, CFM 真实 meta-order tag 不可得; Tokyo Stock Exchange 完整 broker-tag 数据见 Sato & Kanazawa 2024 的 strict universality 复现)

## 与我们 LOBSTER 数据的对应
- LOBSTER 没有 broker / parent-order tag, 必须 heuristic cluster
- 简化复现: 同 ticker × 同 side × 时间 gap < 60s 的连续 trades 聚合为 proxy meta-order
- 限制: heuristic 重建会引入 mis-grouping noise, 实测 exponent 可能偏离 0.5 (经验范围 0.4–0.6 都视为支持 sqrt law); aggressive vs passive split 也会改变结果
- 建议: 先在单 ticker 单日做 sanity check, 再扩展到全数据集; 报告时给出 heuristic 参数的 sensitivity 分析

## Best Model So Far

> **任务核心数字**: impact exponent $\delta \approx 0.5$, normalized slope $Y \approx 0.5$
>
> Auto Research 三栏 (paper / classical / mamba3-generated)：

| Stream | Source | $\hat \delta$ | $\hat Y$ | Status |
|--------|--------|---------------|----------|--------|
| **A. Reference (paper)** | Toth et al. 2011, CFM proprietary, multi-asset | 0.5 (small-tick) / 0.6 (large-tick) | ~0.5 | published |
| **B. Classical estimator on LOBSTER** | Heuristic meta-order cluster + log-log OLS on 8 tickers × 4 yr | TBD | TBD | _pending — 见复现协议; 经验范围 0.4-0.6 都视为支持 sqrt law_ |
| **C. mamba3 generated samples** | Same heuristic on synthetic trade stream from mamba3 SOTA | TBD | TBD | _pending — uses mamba3 ckpt pw8u0edj@46050_ |

**关联 model card**: 评估 mamba3 generated samples 用的 ckpt 见 [`models/mamba3.md`](../models/mamba3.md) → step 46050 of pw8u0edj。

**复现 ckpt + commit pinning**:
```bash
git clone git@github.com:KangOxford/LOBS5.git
cd LOBS5
git checkout 3f6d32a6d8ec79bd24e91dd9ec5fc18c43ad3f28   # mamba3 paper baseline state
# generate 全天连续 trade stream → cluster meta-orders → log-log fit
```

**预期判定**：
- Stream B (real LOBSTER): $\hat \delta \in [0.4, 0.6]$ ✓
- Stream C (mamba3 generated): $\hat \delta \in [0.4, 0.6]$ → mamba3 capture 了 critical liquidity stylized fact;
  否则 generative model 对 latent order book 的 V-shape 假设失真

## 引用
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
