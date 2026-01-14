# 建议的模型参数调整

## 方案1：调整 LightGBM 参数（在 workflow_config 中）

```yaml
task:
    model:
        class: LGBModel
        module_path: qlib.contrib.model.gbdt
        kwargs:
            early_stopping_rounds: 50      # 从100减少到50
            num_boost_round: 500           # 从1000减少到500
            learning_rate: 0.05            # 从0.01增加到0.05
            num_leaves: 15                 # 从31减少到15（防止过拟合）
            max_depth: 5                   # 添加深度限制
            subsample: 0.8                 # 保持
            colsample_bytree: 0.8          # 保持
            lambda_l2: 0.1                 # 从1.0减少到0.1（减少正则化）
            min_child_samples: 20          # 添加最小样本数
            num_threads: 8
            verbosity: 1                   # 增加日志详细度
```

## 方案2：检查特征方差

运行以下脚本检查特征是否有足够的方差：

```python
import qlib
from qlib.contrib.data.handler import CryptoAlpha158WithFunding

qlib.init(provider_uri="data/qlib_data/crypto")

handler = CryptoAlpha158WithFunding(
    instruments="crypto_4h",
    start_time="2020-01-01",
    end_time="2024-12-31",
    freq="240min"
)

data = handler.fetch()

# 检查特征方差
variances = data.var()
print("特征方差统计：")
print(variances.describe())

# 找出低方差特征
low_var = variances[variances < 1e-8]
print(f"\n低方差特征数量: {len(low_var)}")

# 检查 funding rate 特征
funding_cols = [col for col in data.columns if 'funding' in str(col).lower()]
print(f"\nFunding rate 特征方差：")
for col in funding_cols:
    print(f"{col}: {variances[col]}")
```

## 方案3：增加 Funding Rate 数据

当前只有100条记录，建议：
1. 获取更多历史 funding rate 数据
2. 或者调整训练期间，只使用有 funding rate 数据的时间段

## 方案4：调整标签定义

在 workflow_config 中添加自定义标签：

```yaml
task:
    dataset:
        kwargs:
            handler:
                kwargs:
                    label: ["Ref($close, -6)/Ref($close, -1) - 1"]  # 预测未来6个4小时周期（24小时）
```

## 方案5：禁用 SigAnaRecord 避免错误

在 workflow_config 中移除 SigAnaRecord：

```yaml
task:
    record: 
        - class: SignalRecord
          module_path: qlib.workflow.record_temp
          kwargs: 
            model: <MODEL>
            dataset: <DATASET>
        # 注释掉 SigAnaRecord
        # - class: SigAnaRecord
        #   module_path: qlib.workflow.record_temp
        #   kwargs: 
        #     ana_long_short: True
        #     ann_scaler: 2190
        - class: PortAnaRecord
          module_path: qlib.workflow.record_temp
          kwargs: 
            config: *port_analysis_config
```
