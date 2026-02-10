# 目标

构建一个**可长期盈利、可实盘运行**的加密货币回测与交易系统，支持合约交易。系统以**风险控制优先**为原则，通过多时间尺度决策、1 分钟微观结构异常检测、Regime 控制与范围（Range）预测，避免假突破、插针等常见亏损来源。

---

# 一、核心设计原则（已冻结）

1. **系统 ≠ 模型**：模型只负责提供信息，不直接决定交易。
2. **Regime First**：错误市场状态下宁可不交易。
3. **分层时间尺度**：
   - 高周期（15m / 1h / 4h）决定“是否下注、往哪边”。
   - 低周期（1m）决定“怎么下注、怎么活下来”。
4. **PnL 是路径依赖的**：不仅预测 close，还要预测未来可达价格区间（high / low）。
5. **异常驱动风控**：1m 只做异常检测，不做方向预测。

---

# 二、总体系统架构

```
Market Data
   ↓
Regime Engine（4h / 1h）
   ↓
Signal & Range Models（15m / 1h / 4h）
   ↓
Decision Aggregator（方向 + RR 可行性）
   ↓
Structure State Machine（插针 / 假突破 / 真突破）
   ↓
1m Execution & Risk Engine
   ↓
Exchange
```

---

# 三、时间尺度职责划分

## 1. 4h 级别（结构层）

- 市场大状态：Trend / Range / High Vol
- 是否允许趋势类交易
- 禁止频繁反向

## 2. 1h 级别（主决策层）

- 主要方向（Long / Short）
- Regime 判定（TREND_OK / EXTREME / NO_TRADE）
- 未来 4h Range 预测（核心）

## 3. 15m 级别（时机过滤层）

- Pullback / Breakout 过滤
- 防止追高、杀跌

## 4. 1m 级别（执行与生存层）

- 异常检测（波动、成交量、结构）
- 精确入场
- 动态止损 / 减仓 / 强平
- 不参与方向预测

---

# 四、Regime Engine（是否允许交易）

## 输入

- EMA 结构（EMA50 / EMA200）
- 波动率（ATR、Vol Ratio）
- 价格位置（Z-score、分位）

## 输出状态

- NO_TRADE
- TREND_OK
- TREND_EXTREME
- RANGE
- HIGH_VOL

## 决策逻辑（简化）

- 高波动 → NO_TRADE
- 有趋势 + 非极端乖离 → TREND_OK
- 有趋势 + 极端乖离 → TREND_EXTREME
- 无趋势 → RANGE

---

# 五、1 分钟异常检测模块（Anomaly Detector）

## 目标

只回答一个问题：**当前 K 线是否“不正常”**。

## 异常类型

1. **波动异常**：Range / ATR 过大（插针候选）
2. **结构异常**：Wick ≫ Body（扫流动性）
3. **成交量异常**：放量不走（假突破）

## 输出

- anomaly_score ∈ [0, 1]
- event_type：SPIKE / FAILED_BREAK / LIQUIDITY

---

# 六、结构状态机（Structure State Machine）

## 状态定义

- NORMAL
- SPIKE_LIQUIDITY（插针 / 扫流动性）
- FAILED_BREAKOUT（假突破）
- ACCEPTED_BREAKOUT（真突破）

## 状态来源

- 1m 异常事件 + 15m / 1h 结构确认

## 状态 → 系统行为

| 状态              | 行为                   |
| ----------------- | ---------------------- |
| SPIKE_LIQUIDITY   | 禁止追单，等待反向结构 |
| FAILED_BREAKOUT   | 禁止顺势交易           |
| ACCEPTED_BREAKOUT | 允许顺势，放宽仓位     |

---

# 七、Range-aware 模型设计（核心升级）

## 预测目标（未来 4h）

1. **Direction**：上涨 / 下跌概率
2. **Upside**：最大有利波动（MFE）
3. **Downside**：最大不利波动（MAE）
4. **Volatility**：区间宽度

## 交易许可条件

- P(direction) > 阈值
- Upside / |Downside| ≥ 最小 RR
- Downside ≤ 风险上限

---

# 八、交易与风险控制逻辑

## 动态止损

- 基于预测 downside
- 结合 1m 结构止损

## 动态止盈

- 基于预测 upside
- 防止贪婪

## 仓位大小

- position ∝ 1 / predicted_downside
- Regime / Structure 状态调整仓位上限

## 实时风控

- 1m anomaly_score 超阈值 → 减仓 / 平仓

---

# 九、回测与验证要求（必须满足）

- Walk-forward（滚动训练 / 测试）
- 多时间尺度信息隔离（防数据泄漏）
- 滑点、手续费、最小下单量模拟
- Regime / Structure 分段绩效分析

---

# 十、执行计划（逐步实施）

## Phase 1：基础框架（2–3 周）

- 数据管道（1m / 15m / 1h / 4h）
- Regime Engine
- 1m Anomaly Detector

## Phase 2：Range 模型（2–3 周）

- 构建 4h Upside / Downside 标签
- 训练多输出模型
- 验证 RR 过滤效果

## Phase 3：结构状态机（1–2 周）

- 插针 / 假突破 / 真突破逻辑
- 接入交易许可矩阵

## Phase 4：完整回测（2 周）

- 多币种（BTC / ETH 起）
- 回撤、稳定性评估

## Phase 5：实盘准备

- Shadow trading
- 风控阈值冻结
- 小资金实盘

---

# 十一、最终目标

- 系统在错误市场中**自动不交易**
- 盈亏分布可控、回撤可解释
- 能长期运行，而非短期回测幻觉

**这是一个“生存优先、利润其次、长期为王”的交易系统。**
