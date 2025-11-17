# 数据正确性和完整性验证指南

## 概述

在量化交易系统中，数据的正确性和完整性直接影响策略的准确性和可靠性。本指南提供了全面的数据验证方法，确保下载的加密货币数据符合质量标准。

## 验证维度

### 1. 数据完整性检查
- **缺失数据检测**: 检查是否存在空值或缺失的OHLCV数据
- **时间序列连续性**: 验证数据的时间戳是否连续，无跳跃
- **交易对覆盖**: 确保所有预期的交易对都有数据

### 2. 数据正确性检查
- **价格合理性**: 检查价格数据是否在合理范围内
- **成交量验证**: 验证成交量数据的合理性
- **数据一致性**: 确保高开低收价格关系正确 (High >= Open, High >= Close, Low <= Open, Low <= Close)

### 3. 数据质量检查
- **异常值检测**: 识别价格或成交量的异常波动
- **重复数据**: 检查是否存在重复的时间戳
- **数据类型**: 验证数据类型和格式正确

## 验证工具和脚本

### 1. 基础数据质量检查

```bash
# 激活环境
conda activate qlib

# 运行基础数据质量检查
python scripts/check_data_quality.py
```

**检查内容:**
- 数据目录存在性
- 交易对数量和列表
- 特征文件数量
- 日历文件存在性
- 日期范围验证

### 2. 详细数据健康检查

```bash
# 检查Qlib格式数据的健康状况
python scripts/check_data_health.py --qlib_dir data/qlib_data/crypto --freq 15min
```

**检查内容:**
- 缺失数据检测
- 大幅波动检查 (默认价格阈值: 0.5, 成交量阈值: 3)
- 必需列检查 (OHLCV)
- factor列验证

### 3. 二进制数据一致性检查

```bash
# 比较原始CSV和转换后的二进制数据一致性
python scripts/check_dump_bin.py --qlib_dir data/qlib_data/crypto --csv_path data/csv_data
```

**检查内容:**
- 原始数据 vs 转换后数据一致性
- 数据精度验证
- 字段匹配检查

### 4. PostgreSQL数据验证

```python
from scripts.postgres_storage import PostgresStorage

# 初始化存储
storage = PostgresStorage()

# 健康检查
is_healthy = storage.health_check()
print(f"数据库连接健康: {is_healthy}")

# 数据完整性检查
storage.validate_data_integrity()
```

**检查内容:**
- 数据库连接状态
- 表结构完整性
- 分区存在性
- 数据重复检查

## 手动验证方法

### 1. 时间序列连续性检查

```python
import pandas as pd
from qlib.data import D

# 加载数据
df = D.features(['BTCUSDT'], ['$open', '$close', '$high', '$low', '$volume'], freq='15min')

# 检查时间间隔
time_diffs = df.index.get_level_values('datetime').diff()
expected_interval = pd.Timedelta('15min')

# 找出不连续的时间点
gaps = time_diffs[time_diffs > expected_interval]
print(f"发现 {len(gaps)} 个时间间隔异常")
```

### 2. 价格合理性检查

```python
# 检查价格关系
invalid_high = df[df['$high'] < df[['$open', '$close']].max(axis=1)]
invalid_low = df[df['$low'] > df[['$open', '$close']].min(axis=1)]

print(f"无效高价记录: {len(invalid_high)}")
print(f"无效低价记录: {len(invalid_low)}")

# 检查价格波动幅度
price_change_pct = df['$close'].pct_change().abs()
extreme_changes = price_change_pct[price_change_pct > 0.5]  # 50% 以上波动
print(f"极端价格变动: {len(extreme_changes)}")
```

### 3. 成交量异常检测

```python
# 检查成交量为0的记录
zero_volume = df[df['$volume'] == 0]
print(f"成交量为0的记录: {len(zero_volume)}")

# 检查成交量异常波动
volume_change_pct = df['$volume'].pct_change().abs()
extreme_volume_changes = volume_change_pct[volume_change_pct > 10]  # 10倍以上波动
print(f"极端成交量变动: {len(extreme_volume_changes)}")
```

### 4. 数据覆盖率检查

```python
# 检查数据覆盖率
total_expected_periods = len(pd.date_range(start='2024-01-01', end='2024-12-31', freq='15min'))
actual_periods = len(df)
coverage_rate = actual_periods / total_expected_periods

print(f"数据覆盖率: {coverage_rate:.2%}")
print(f"缺失数据比例: {(1 - coverage_rate):.2%}")
```

## 自动化验证脚本

### 创建综合验证脚本

```python
#!/usr/bin/env python3
"""
综合数据验证脚本
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from scripts.config_manager import ConfigManager
from scripts.postgres_storage import PostgresStorage

def validate_data_completeness():
    """验证数据完整性"""
    print("🔍 数据完整性验证...")

    config = ConfigManager()
    data_dir = config.config.get('data', {}).get('bin_data_dir', 'data/qlib_data/crypto')

    # 检查文件存在性
    instruments_file = Path(data_dir) / "instruments" / "all.txt"
    if not instruments_file.exists():
        raise FileNotFoundError(f"Instruments file not found: {instruments_file}")

    # 检查特征文件
    features_dir = Path(data_dir) / "features"
    if not features_dir.exists():
        raise FileNotFoundError(f"Features directory not found: {features_dir}")

    print("✅ 数据文件完整性检查通过")

def validate_data_correctness():
    """验证数据正确性"""
    print("🔍 数据正确性验证...")

    from qlib.data import D
    import qlib

    qlib.init(provider_uri='data/qlib_data/crypto')

    instruments = D.instruments(market='all')
    sample_instrument = list(instruments)[:1][0]  # 取第一个交易对

    df = D.features([sample_instrument], ['$open', '$close', '$high', '$low', '$volume'], freq='15min')

    # 检查OHLC关系
    invalid_ohlc = (
        (df['$high'] < df['$open']) |
        (df['$high'] < df['$close']) |
        (df['$low'] > df['$open']) |
        (df['$low'] > df['$close'])
    )

    if invalid_ohlc.any():
        print(f"⚠️ 发现 {invalid_ohlc.sum()} 个OHLC关系异常的记录")
    else:
        print("✅ OHLC关系验证通过")

    # 检查缺失值
    missing_data = df.isnull().sum().sum()
    if missing_data > 0:
        print(f"⚠️ 发现 {missing_data} 个缺失数据点")
    else:
        print("✅ 无缺失数据")

def validate_database_integrity():
    """验证数据库完整性"""
    print("🔍 数据库完整性验证...")

    try:
        storage = PostgresStorage()
        is_healthy = storage.health_check()

        if is_healthy:
            print("✅ 数据库连接正常")
        else:
            print("❌ 数据库连接异常")

    except Exception as e:
        print(f"❌ 数据库验证失败: {e}")

if __name__ == "__main__":
    try:
        validate_data_completeness()
        validate_data_correctness()
        validate_database_integrity()
        print("🎉 所有验证通过!")
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        sys.exit(1)
```

## 定期验证建议

### 1. 数据下载后验证
每次运行数据收集器后，自动执行验证:

```bash
# 在数据收集脚本后添加验证
python scripts/okx_data_collector.py --output db
python scripts/check_data_quality.py
python scripts/check_data_health.py --qlib_dir data/qlib_data/crypto --freq 15min
```

### 2. 定时监控
设置定时任务监控数据质量:

```bash
# crontab 示例 (每天早上8点检查)
0 8 * * * cd /path/to/project && conda activate qlib && python scripts/check_data_quality.py
```

### 3. 异常告警
当检测到数据质量问题时发送告警:

```python
import smtplib
from email.mime.text import MIMEText

def send_alert(subject, message):
    # 配置邮件告警
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = 'alert@trading-system.com'
    msg['To'] = 'admin@trading-system.com'

    # 发送邮件逻辑...
    pass

# 在验证脚本中使用
if data_quality_issues:
    send_alert("数据质量告警", f"发现 {len(issues)} 个数据质量问题")
```

## 常见问题和解决方案

### 1. 时间戳不连续
**问题**: 数据中有时间间隔异常
**解决**: 检查数据收集器的频率设置，确保定时任务正常运行

### 2. 价格数据异常
**问题**: 价格波动过大或价格关系错误
**解决**: 验证交易所API数据源，检查数据转换逻辑

### 3. 成交量为0
**问题**: 某些时间段成交量为0
**解决**: 可能是交易所数据问题，考虑使用多个数据源交叉验证

### 4. 数据库连接问题
**问题**: 无法连接PostgreSQL数据库
**解决**: 检查数据库配置和网络连接

## 总结

数据验证是量化交易系统的重要组成部分。通过多层次的验证方法，可以确保数据的正确性和完整性，为策略开发和回测提供可靠的数据基础。

建议在数据管道的每个关键节点都加入验证步骤，形成完整的质量 assurance 体系。