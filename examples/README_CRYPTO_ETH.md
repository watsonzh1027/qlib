# ETH Crypto Trading Workflow with Funding Rates

本目录包含完整的 ETH 加密货币交易工作流，集成了资金费率特征。

## 📁 文件结构

```
examples/
├── benchmarks/LightGBM/
│   └── workflow_config_lightgbm_crypto_eth.yaml  # 工作流配置文件
├── run_crypto_eth_workflow.py                     # 主执行脚本
qlib/contrib/data/
└── handler_crypto.py                              # 增强的数据处理器（含资金费率）
scripts/
└── fetch_funding_rates.py                         # 资金费率数据获取工具
```

## 🚀 快速开始

### 1. 运行完整工作流

```bash
conda activate qlib
python examples/run_crypto_eth_workflow.py
```

该脚本会自动执行以下步骤：
1. ✅ 获取资金费率数据（如果尚未存在）
2. ✅ 准备训练数据集（Alpha158 + 资金费率特征）
3. ✅ 训练 LightGBM 模型
4. ✅ 生成预测信号
5. ✅ 运行回测（使用优化后的策略参数）
6. ✅ 生成性能报告

### 2. 自定义配置

编辑 `workflow_config_lightgbm_crypto_eth.yaml` 来调整：

```yaml
# 数据时间范围
data_handler_config:
    start_time: 2022-01-01
    end_time: 2025-12-31

# 模型参数
task:
    model:
        kwargs:
            learning_rate: 0.01
            num_leaves: 31
            max_depth: -1

# 策略参数（已优化）
port_analysis_config:
    strategy:
        kwargs:
            signal_threshold: 0.09  # 信号阈值
            take_profit: 0.05       # 止盈 5%
            stop_loss: -0.07        # 止损 -7%
```

## 📊 特征说明

### Alpha158 基础特征（525 个）
- KLEN, KMID, KUP, KLOW 等 K 线形态特征
- ROC, MA, STD 等技术指标
- QTLU, QTLD 等分位数特征
- CORR, CORD 等相关性特征

### 资金费率特征（9 个）
| 特征名 | 说明 | 用途 |
|--------|------|------|
| `funding_rate` | 原始资金费率 | 市场多空情绪 |
| `funding_rate_ma7` | 7 期均值 | 短期趋势 |
| `funding_rate_ma30` | 30 期均值 | 长期趋势 |
| `funding_rate_std7` | 7 期标准差 | 短期波动 |
| `funding_rate_std30` | 30 期标准差 | 长期波动 |
| `funding_rate_extreme` | 极端费率标记 | 异常检测 |
| `funding_rate_zscore` | Z-score 标准化 | 相对强度 |
| `funding_rate_momentum` | 变化率 | 动量信号 |
| `funding_rate_cumsum` | 累计费率 | 长期偏向 |

**资金费率解读：**
- **正值**：多头支付空头 → 市场偏多
- **负值**：空头支付多头 → 市场偏空
- **极端值** (|rate| > 0.1%)：强烈的单边情绪

## 🎯 优化参数说明

当前配置使用了通过网格搜索找到的最优参数：

```yaml
signal_threshold: 0.09    # 只在预测收益 > 9% 时入场
take_profit: 0.05         # 5% 止盈（适合 4H 周期）
stop_loss: -0.07          # -7% 止损（平衡风险）
```

**历史表现（2025 测试集）：**
- Sharpe Ratio: **0.42**
- Annualized Return: **18.3%**
- Max Drawdown: **-35.8%**

## 🔧 高级用法

### 仅获取资金费率数据

```bash
python scripts/fetch_funding_rates.py
```

### 使用自定义配置文件

```bash
python examples/run_crypto_eth_workflow.py --config path/to/your/config.yaml
```

### 在 Jupyter Notebook 中使用

```python
from qlib.contrib.data.handler_crypto import CryptoAlpha158WithFunding

# 初始化处理器
handler = CryptoAlpha158WithFunding(
    instruments=['eth_usdt_4h_future', 'btc_usdt_4h_future'],
    start_time='2024-01-01',
    end_time='2025-01-01',
    funding_rate_dir='data/funding_rates'
)

# 获取特征
df = handler.fetch_data()
print(df.head())
```

## 📈 结果分析

工作流完成后，结果保存在 `mlruns/` 目录：

```
mlruns/
└── <experiment_id>/
    └── <run_id>/
        └── artifacts/
            ├── pred.pkl                          # 预测结果
            ├── sig_analysis/                     # 信号分析
            └── portfolio_analysis/
                └── report_normal_240min.pkl      # 回测报告
```

使用 MLflow UI 查看：
```bash
mlflow ui
```

## ⚠️ 注意事项

1. **数据依赖**：确保已运行数据收集脚本，生成 `data/qlib_data/crypto/` 目录
2. **资金费率**：首次运行会自动下载，后续运行会跳过已存在的文件
3. **内存需求**：多币种训练需要约 4-8GB 内存
4. **训练时间**：完整训练约需 5-10 分钟（取决于 CPU）

## 🔄 持续优化建议

1. **增加币种**：扩展到市值前 50 的币种以提高泛化能力
2. **动态仓位**：根据信号强度动态调整杠杆
3. **集成 OI**：添加持仓量（Open Interest）特征
4. **滚动训练**：实现在线学习以适应市场变化

## 📚 参考资料

- [Qlib 官方文档](https://qlib.readthedocs.io/)
- [OKX API 文档](https://www.okx.com/docs-v5/en/)
- [资金费率机制说明](https://www.okx.com/support/hc/en-us/articles/360053909272)
