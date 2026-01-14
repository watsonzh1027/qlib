# SigAnaRecord 模块说明

## 功能概述

**SigAnaRecord (Signal Analysis Record)** 是 Qlib 中用于**评估模型预测信号质量**的分析模块。

## 核心功能

### 1. IC 分析（Information Coefficient）

**作用**：衡量预测信号与实际收益的相关性

**计算指标**：
- **IC (信息系数)**：预测值与真实标签的 Pearson 相关系数
  - 范围：-1 到 1
  - IC > 0.05：较好的信号
  - IC > 0.10：优秀的信号
  
- **ICIR (IC 信息比率)**：IC 的稳定性
  - 计算：IC.mean() / IC.std()
  - ICIR > 1.0：信号稳定
  - ICIR > 2.0：信号非常稳定

- **Rank IC / Rank ICIR**：使用 Spearman 秩相关（更鲁棒）

### 2. Long-Short 分析

**作用**：评估做多做空策略的潜在收益

**计算指标**：
- **Long-Short Ann Return**：做多 top 20% + 做空 bottom 20% 的年化收益
- **Long-Short Ann Sharpe**：Long-Short 策略的夏普比率
- **Long-Avg Ann Return**：只做多 top 20% 的年化收益
- **Short-Avg Ann Return**：只做空 bottom 20% 的年化收益

### 3. 输出文件

生成以下分析文件：
- `ic.pkl`：每日 IC 时间序列
- `ric.pkl`：每日 Rank IC 时间序列
- `long_short_r.pkl`：Long-Short 收益序列
- `long_avg_r.pkl`：Long 收益序列
- `short_avg_r.pkl`：Short 收益序列

## 典型输出示例

```
Signal Analysis Metrics:
{
    'IC': 0.052,                      # 平均信息系数
    'ICIR': 1.25,                     # IC 信息比率
    'Rank IC': 0.048,                 # 秩相关 IC
    'Rank ICIR': 1.18,                # 秩相关 ICIR
    'Long-Short Ann Return': 0.156,   # 15.6% 年化收益
    'Long-Short Ann Sharpe': 1.82,    # 夏普比率 1.82
    'Long-Avg Ann Return': 0.089,     # 8.9% 做多收益
    'Short-Avg Ann Return': -0.067    # -6.7% 做空收益
}
```

## 重要性评估

### ✅ 优点：
1. **量化评估**：提供客观的信号质量指标
2. **行业标准**：IC/ICIR 是量化交易的标准评估方法
3. **策略验证**：帮助判断模型是否真的学到了有用的模式
4. **性能预测**：IC 高的模型通常在实盘中表现更好

### ⚠️ 局限性：
1. **非必需**：不影响模型训练和预测生成
2. **后处理**：只是分析工具，不参与交易决策
3. **可替代**：可以通过回测结果间接评估

## 当前问题

### 错误信息：
```
KeyError: 'datetime'
```

### 原因：
- `calc_ic` 函数期望 datetime 是列名
- 但在 MultiIndex 数据中，datetime 是索引级别
- 导致 `groupby('datetime')` 失败

### 影响：
- ❌ 无法生成 IC/ICIR 等分析指标
- ✅ 不影响模型训练
- ✅ 不影响预测生成
- ✅ 不影响回测执行

## 解决方案

### 方案1：暂时禁用（推荐）

在 `workflow_config.yaml` 中注释掉：
```yaml
# - class: SigAnaRecord
#   module_path: qlib.workflow.record_temp
#   kwargs: 
#     ana_long_short: True
#     ann_scaler: 2190
```

**优点**：
- ✅ 立即解决问题
- ✅ 不影响其他功能
- ✅ 可以通过回测结果评估模型

### 方案2：修复 calc_ic 函数

修改 `/home/watson/work/qlib/qlib/contrib/eva/alpha.py` 中的 `calc_ic` 函数：

```python
def calc_ic(pred, label, date_col="datetime"):
    # 如果 datetime 是索引级别而不是列
    if isinstance(pred.index, pd.MultiIndex) and date_col in pred.index.names:
        df = pd.DataFrame({"pred": pred, "label": label})
        # 使用 level 参数而不是列名
        ic = df.groupby(level=date_col, group_keys=False).apply(
            lambda df: df["pred"].corr(df["label"])
        )
    else:
        # 原有逻辑
        df = pd.DataFrame({"pred": pred, "label": label})
        ic = df.groupby(date_col, group_keys=False).apply(
            lambda df: df["pred"].corr(df["label"])
        )
    return ic, ric
```

**优点**：
- ✅ 保留完整功能
- ✅ 获得 IC/ICIR 指标

**缺点**：
- ⚠️ 需要修改 Qlib 核心代码
- ⚠️ 可能影响其他使用该函数的地方

## 建议

### 当前阶段：
**使用方案1（禁用 SigAnaRecord）**

原因：
1. 您正在调试模型性能问题
2. 回测结果（收益、夏普比率）已经足够评估模型
3. 避免被非关键错误干扰

### 未来阶段：
当模型性能改善后，如果需要详细的信号质量分析，可以：
1. 实施方案2修复函数
2. 或者编写自定义分析脚本计算 IC/ICIR

## 替代方案

即使不使用 SigAnaRecord，您仍然可以通过以下方式评估模型：

1. **PortAnaRecord**（回测分析）：
   - 年化收益率
   - 夏普比率
   - 最大回撤
   - 胜率

2. **自定义分析**：
   ```python
   import pandas as pd
   
   # 加载预测和标签
   pred = pd.read_pickle('pred.pkl')
   label = pd.read_pickle('label.pkl')
   
   # 计算 IC
   ic = pred.corrwith(label, method='pearson')
   print(f"IC: {ic.mean():.4f}")
   print(f"ICIR: {ic.mean() / ic.std():.4f}")
   ```

## 总结

- **功能**：信号质量分析工具
- **重要性**：中等（有用但非必需）
- **当前状态**：因 MultiIndex 问题暂时禁用
- **影响**：不影响核心训练和预测流程
- **建议**：暂时禁用，专注于改善模型性能
