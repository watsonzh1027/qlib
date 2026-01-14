# OKX Funding Rate API 限制问题分析

## 问题描述

使用 `ccxt.okx().fetch_funding_rate_history()` 获取历史资金费率数据时，发现：
- 请求时间范围：2023-01-01 到 2025-01-15（2年）
- 实际返回数据：2025-10-13 到 2025-11-15（1个月）
- 返回记录数：100条

## 根本原因

**OKX API 限制**：
1. `fetch_funding_rate_history` 只返回**最近的**资金费率数据
2. `since` 参数被忽略或有特殊限制
3. 最多只能获取最近100条记录（约33天，每天3次结算）

## 验证

```python
# 请求从 2023-01-01 开始的数据
funding_rates = exchange.fetch_funding_rate_history(
    "ETH/USDT:USDT",
    since=1672560000000,  # 2023-01-01
    limit=100
)

# 实际返回
第一条: 2025-10-13  # ← 不是 2023-01-01！
最后一条: 2025-11-15
```

## 解决方案

### 方案1：使用 OKX 原生 REST API（推荐）

OKX 提供了专门的历史数据 API：

**API 端点**：
```
GET /api/v5/public/funding-rate-history
```

**参数**：
- `instId`: 产品ID（如 ETH-USDT-SWAP）
- `before`: 请求此时间戳之前的数据
- `after`: 请求此时间戳之后的数据
- `limit`: 返回数量（最多100）

**特点**：
- ✅ 支持真正的历史数据查询
- ✅ 可以通过分页获取完整历史
- ✅ 数据可追溯到合约上线时间

**实现**：
```python
import requests
import time
from datetime import datetime

def fetch_okx_funding_history(inst_id, start_date, end_date):
    """
    使用 OKX REST API 获取完整历史数据
    """
    url = "https://www.okx.com/api/v5/public/funding-rate-history"
    
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
    
    all_data = []
    after_ts = start_ts
    
    while after_ts < end_ts:
        params = {
            'instId': inst_id,
            'after': str(after_ts),
            'limit': '100'
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['code'] != '0':
            print(f"API 错误: {data['msg']}")
            break
        
        records = data['data']
        if not records:
            break
        
        all_data.extend(records)
        
        # 更新时间戳
        after_ts = int(records[-1]['fundingTime']) + 1
        
        print(f"已获取 {len(all_data)} 条，最新: {records[-1]['fundingTime']}")
        time.sleep(0.2)  # 避免限流
    
    return all_data
```

### 方案2：使用其他数据源

如果 OKX 历史数据有限，可以考虑：

1. **Binance API**：
   - 提供更长的历史数据
   - API 更稳定
   ```python
   exchange = ccxt.binance()
   funding_rates = exchange.fetch_funding_rate_history('ETH/USDT:USDT')
   ```

2. **CryptoCompare**：
   - 专业的加密货币数据提供商
   - 有免费 API

3. **下载历史数据文件**：
   - 从数据提供商购买/下载完整历史数据
   - 一次性导入

### 方案3：接受现有数据限制

如果只能获取最近100条记录：

**调整策略**：
```yaml
# 使用最近1个月的数据进行训练
data_handler_config:
    start_time: 2025-10-13  # 与 funding rate 开始时间一致
    end_time: 2025-11-15    # 与 funding rate 结束时间一致
    
dataset:
    segments:
        train: [2025-10-13, 2025-11-05]  # 3周训练
        valid: [2025-11-06, 2025-11-10]  # 5天验证
        test: [2025-11-11, 2025-11-15]   # 5天测试
```

**缺点**：
- ❌ 数据太少，模型无法充分学习
- ❌ 过拟合风险极高
- ❌ 不适合实际应用

## 推荐行动方案

### 立即执行：使用 OKX REST API

1. 创建新的获取脚本使用原生 API
2. 获取2年完整历史数据
3. 保存为 CSV 格式

### 备选方案：切换到 Binance

如果 OKX 数据仍然有限：
1. 尝试 Binance API
2. 验证数据可用性
3. 如果可行，切换数据源

## 下一步

我将创建一个使用 OKX REST API 的新脚本来获取完整历史数据。
