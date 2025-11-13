# 预测信号详解：`pred = self.model.predict(self.dataset)`

## 预测信号的本质

**预测信号是模型对未来价格变动的数值预测**，具体来说是：

```python
pred = self.model.predict(self.dataset)
```

这段代码生成的 `pred` 是 **对未来收盘价的回归预测值**。

## 数据流分析

### 1. 训练时的标签构造
从配置文件可以看到：
```json
"data_loader": {
  "class": "QlibDataLoader",
  "kwargs": {
    "config": {
      "feature": ["$open", "$high", "$low", "$close", "$volume"],
      "label": ["$close"]
    }
  }
}
```

- **特征 (features)**：当前周期的 OHLCV 数据
  - `$open`：开盘价
  - `$high`：最高价
  - `$low`：最低价
  - `$close`：收盘价
  - `$volume`：成交量

- **标签 (label)**：`["$close"]` 表示 **下一周期的收盘价**

### 2. 模型训练目标
```python
"loss": "mse"  # 均方误差损失函数
```
模型训练的目标是最小化预测值与实际下一周期收盘价之间的均方误差。

### 3. 预测结果的含义

**预测信号 `pred` 表示：**
- **数值范围**：通常是正实数，表示预测的下一周期收盘价
- **单位**：与原始价格数据相同的单位（美元、加密货币计价单位）
- **时间跨度**：预测下一周期的价格（例如，15分钟后的价格）

## 预测结果的数据结构

```python
# 预测结果示例
                            score
datetime   instrument
2025-11-05 AAVEUSDT    205.212610
           ADAUSDT      25.328295
           AVAXUSDT     35.598110
           BCHUSDT     325.441508
           BNBUSDT     651.261038
```

- **索引**：`datetime`（预测日期） + `instrument`（交易对）
- **值**：预测的下一周期收盘价

## 信号转换为交易决策

在量化交易中，预测的绝对价格值通常转换为**相对变动信号**：

### 方法1：与当前价格比较
```python
# 计算预测收益率
predicted_return = (predicted_price - current_price) / current_price
```

### 方法2：标准化为分数
```python
# 将预测价格转换为标准化的预测分数
signal_score = (predicted_price - mean_price) / std_price
```

### 方法3：使用残差
```python
# 预测价格相对于当前价格的变化
price_change = predicted_price - current_price
```

## 在回测中的应用

在 `TopkDropoutStrategy` 策略中：
- 选择预测分数最高的 **topk** 个股票（默认50个）
- 排除预测分数最低的 **n_drop** 个股票（默认5个）
- 对剩余股票等权重分配资金

## 信号质量评估

信号质量通过以下指标评估：
- **IC (Information Coefficient)**：预测值与实际收益的相关性
- **Rank IC**：预测排名与实际收益排名的相关性
- **预测准确性**：预测方向的正确率

## 关键特性

1. **回归预测**：预测具体的价格数值，而非分类标签
2. **未来导向**：预测下一周期的价格，用于提前决策
3. **多资产**：同时为所有交易对生成预测
4. **时间序列**：覆盖整个测试时间段的逐周期预测

## 实际意义

这个预测信号是量化交易系统的核心，它将历史价格数据转换为对未来的价格预期，为交易决策提供科学依据。在加密货币市场中，这种基于机器学习的预测可以捕捉价格趋势、波动性和市场情绪等复杂模式。

## 技术实现细节

### LGBModel.predict() 方法
```python
def predict(self, dataset: DatasetH, segment: Union[Text, slice] = "test"):
    if self.model is None:
        raise ValueError("model is not fitted yet!")
    x_test = dataset.prepare(segment, col_set="feature", data_key=DataHandlerLP.DK_I)
    return pd.Series(self.model.predict(x_test.values), index=x_test.index)
```

- 使用测试段的数据进行预测
- 返回 pandas Series，索引与输入数据保持一致
- 预测值是 LightGBM 模型对下一周期收盘价的直接回归预测

### 数据准备过程
- 从数据集中提取特征数据（OHLCV）
- 使用 `DK_I` (infer) 数据键，表示推理阶段的数据
- 特征数据经过预处理后输入模型

### 模型配置
```json
{
  "class": "LGBModel",
  "module_path": "qlib.contrib.model.gbdt",
  "kwargs": {
    "loss": "mse",
    "colsample_bytree": 0.8879,
    "learning_rate": 0.1,
    "subsample": 0.8789,
    "lambda_l1": 205.6999,
    "lambda_l2": 580.9768,
    "max_depth": 8,
    "num_leaves": 210,
    "num_threads": 20,
    "num_boost_round": 100
  }
}
```

这个配置定义了一个复杂的梯度提升决策树模型，用于从历史价格数据中学习价格变动模式。