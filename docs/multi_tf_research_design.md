# 加密货币多时域预测研究方案 (Multi-Timeframe Research Design)

## 1. 研究背景与目的
在加密货币（特别是 ETH）交易中，单一时域（Timeframe）的预测往往面临“噪音过大”或“灵敏度不足”的问题。本方案旨在通过 1h, 4h, 1d 三个维度的并行训练与评估，寻找预测信心（IC/IR）最强的工作时域，并为后续的多尺度信号融合（Ensemble）打下基础。

## 2. 核心优化策略
### 2.1 标签增强 (Label Enhancement)
*   **多期预测 (Multi-Horizon)**：不再仅预测下一根 K 线的收益率，而是预测未来 $N$ 期的平均收益率。例如 1h 级别预测未来 4h 的均值。
*   **波动率缩放 (Volatility Scaling)**：使用 $Label = \frac{Return}{\sigma_{volatility}}$，将预测目标标准化，降低因市场极端波动导致的 Loss 抖动。

### 2.2 流水线自动化 (Automated Pipeline)
*   **统一调度**：一键完成数据下载 -> 归一化 -> Dump Bin -> 自动化训练。
*   **超参独立优化**：每个频率独立的 Optuna Search 空间，适配不同频率的衰减特征。

### 2.3 评估体系
*   **稳定优先**：引入 **Information Ratio (IR)**，即 $IC / \sigma_{IC}$，评估信号在时间维度上的稳定性。
*   **预测倾向性分析**：统计 Positive Predictions 的覆盖率，防止模型陷入极致保守或过度激进的陷阱。

## 3. 实施路径
1.  **数据层**：隔离存储 `qlib_data_1h`, `qlib_data_4h`, `qlib_data_1d`。
2.  **特征层**：使用 Alpha158 + Alpha360 混合特征，针对不同频率设置不同的滞后参数。
3.  **模型层**：采用提升后的 ALSTM-TS 模型。

---
