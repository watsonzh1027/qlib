
# Crypto  Data Feeder 

### 问题：
*** 我计划 采用 cryptofeed 收集 OKX 数据，主要是资金量排名前50的虚拟币，并提供给Qlib 项目进行策略研究 ***



**cryptofeed + OKX + Qlib** 是一个高效、专业且完全开源的量化研究闭环方案。下面我为你 **定制一套完整、可落地的技术方案**，从 **数据采集 → 本地存储 → 格式转换 → 接入 Qlib** 全流程覆盖，重点解决：

- 如何用 `cryptofeed` 精准收集 **OKX 资金费率排名前50的币种**
- 如何 **定时更新、去重、持久化**
- 如何 **生成 Qlib 所需的 `instruments` 和 `OHLCV` 数据格式**
- 如何 **自动化运行并供 Qlib 直接读取**

---

## 一、整体架构图

```text
OKX WebSocket (via cryptofeed)
        ↓
   cryptofeed → 实时数据流
        ↓
   本地存储 (Parquet + PostgreSQL/MongoDB)
        ↓
   定时任务 (cron / APScheduler)
        ↓
   数据清洗 & 排名筛选 (top 50 by funding rate / volume)
        ↓
   转换为 Qlib 标准格式 (instruments.yaml + .csv/.parquet)
        ↓
   Qlib 策略回测 (qlib.init + QlibDataProvider)
```

---

## 二、核心步骤详解

### 1. 使用 `cryptofeed` 采集 OKX 数据

#### 安装
```bash
pip install cryptofeed pandas pyarrow
```

#### 示例代码：实时采集 OKX 现货 + 永续合约 K线 + 资金费率

```python
# okx_data_collector.py
from cryptofeed import FeedHandler
from cryptofeed.defines import L2_BOOK, TRADES, FUNDING, CANDLES
from cryptofeed.exchanges import OKX
import pandas as pd
from datetime import datetime
import os
from collections import defaultdict
import asyncio

# 存储路径
DATA_DIR = "okx_data"
os.makedirs(DATA_DIR, exist_ok=True)

# 全局存储
klines = defaultdict(list)
funding_rates = {}

# K线回调 (1分钟)
def kline_callback(k, receipt_timestamp):
    symbol = k.symbol
    data = {
        'symbol': symbol,
        'timestamp': k.timestamp,
        'open': k.open,
        'high': k.high,
        'low': k.low,
        'close': k.close,
        'volume': k.volume,
        'interval': k.interval,
    }
    klines[symbol].append(data)

    # 每分钟保存一次
    if len(klines[symbol]) >= 60:  # 假设1m间隔
        save_klines(symbol)

# 资金费率回调
def funding_callback(f, receipt_timestamp):
    funding_rates[f.symbol] = {
        'symbol': f.symbol,
        'funding_rate': f.funding_rate,
        'next_funding_time': f.next_funding_time,
        'timestamp': f.timestamp
    }

def save_klines(symbol):
    if klines[symbol]:
        df = pd.DataFrame(klines[symbol])
        date_str = pd.to_datetime(df['timestamp'], unit='s').dt.strftime('%Y%m%d').iloc[0]
        path = f"{DATA_DIR}/kline_1m/{symbol.replace('/', '_')}_{date_str}.parquet"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_parquet(path, index=False)
        klines[symbol].clear()

def main():
    fh = FeedHandler()

    # 获取 OKX 所有交易对
    exchange = OKX(config={'log_level': 'ERROR'})
    # 注意：cryptofeed 不直接提供全市场列表，可通过 REST 获取
    # 先手动或通过 OKX API 获取 top 50 符号

    symbols = get_top_50_symbols()  # 见下一节

    fh.add_feed(OKX(
        symbols=symbols,
        channels=[CANDLES],
        callbacks={CANDLES: kline_callback}
    ))

    fh.add_feed(OKX(
        symbols=symbols,
        channels=[FUNDING],
        callbacks={FUNDING: funding_callback}
    ))

    fh.run()

if __name__ == '__main__':
    main()
```

---

### 2. 动态获取 **资金费率排名前50的币种**

OKX 官方无直接“资金费率排行”API，但可通过以下方式实现：

#### 方法：每8小时拉取一次所有永续合约的最新资金费率，排序取前50

```python
# get_top50.py
import requests
import pandas as pd
from datetime import datetime
import json

def get_okx_funding_top50():
    url = "https://www.okx.com/api/v5/public/funding-rate"
    all_data = []
    params = {'instType': 'SWAP', 'limit': 100}
    
    while True:
        resp = requests.get(url, params=params).json()
        data = resp['data']
        all_data.extend(data)
        if len(data) < 100:
            break
        params['after'] = data[-1]['fundingTime']

    df = pd.DataFrame(all_data)
    df['fundingRate'] = df['fundingRate'].astype(float).abs()  # 取绝对值
    df = df.sort_values('fundingRate', ascending=False).head(50)
    
    symbols = [s.replace('-SWAP', '') for s in df['instId']]  # 如 BTC-USDT-SWAP → BTC-USDT
    return symbols

# 保存到文件供 cryptofeed 读取
def save_symbols(symbols):
    with open('top50_symbols.json', 'w') as f:
        json.dump(symbols, f)

if __name__ == '__main__':
    top50 = get_okx_funding_top50()
    save_symbols(top50)
    print(f"Top 50 funding rate symbols: {top50}")
```

#### 定时更新 top50（cron）

```bash
# crontab -e
0 */8 * * * cd /path/to/project && python get_top50.py && pkill -f okx_data_collector.py && python okx_data_collector.py &
```

> 说明：每8小时更新一次 top50 符号列表，重启 collector 切换监控对象。

---

### 3. 数据存储：推荐 **Parquet + 分区**

```text
okx_data/
├── kline_1m/
│   ├── BTC_USDT_20250405.parquet
│   ├── ETH_USDT_20250405.parquet
│   └── ...
└── funding/
    └── funding_rates_20250405.parquet
```

优点：列式存储，Qlib 原生支持 Parquet，压缩比高。

---

### 4. 转换为 **Qlib 标准格式**

#### 目录结构（Qlib 要求）

```text
qlib_data/
├── instruments/
│   └── all.txt
├── features/
│   └── day/
│       ├── BTCUSDT.bin
│       └── ETHUSDT.bin
└── calendars/
    └── cn.txt
```

#### 转换脚本（Parquet → Qlib bin）

```python
# convert_to_qlib.py
import qlib
from qlib.data import D
from qlib.constant import Registry
import pandas as pd
import glob
import os

def convert_parquet_to_qlib():
    # 1. 收集所有 symbol
    symbols = set()
    for f in glob.glob("okx_data/kline_1m/*.parquet"):
        symbol = os.path.basename(f).split('_')[0].replace('_', '')
        symbols.add(symbol)

    # 2. 写入 instruments/all.txt
    with open("qlib_data/instruments/all.txt", "w") as f:
        for s in sorted(symbols):
            f.write(f"{s}\t{s}\tSH000000\n")  # Qlib 格式：symbol, name, index

    # 3. 合并所有 K线数据
    all_dfs = []
    for f in glob.glob("okx_data/kline_1m/*.parquet"):
        df = pd.read_parquet(f)
        symbol = os.path.basename(f).split('_')[0].replace('_', '')
        df['symbol'] = symbol
        all_dfs.append(df)

    if all_dfs:
        merged = pd.concat(all_dfs)
        merged['datetime'] = pd.to_datetime(merged['timestamp'], unit='s')
        merged = merged[['symbol', 'datetime', 'open', 'high', 'low', 'close', 'volume']]
        merged = merged.rename(columns={'datetime': 'date'})

        # 4. 初始化 Qlib 并 dump
        qlib.init(provider_uri='qlib_data', region=Registry.REGION_CN)
        from qlib.data.dataset import DatasetD
        DatasetD.dump_features(merged, feature_cols=['open', 'high', 'low', 'close', 'volume'])
```

---

### 5. 自动化全流程（推荐 Docker + cron）

```Dockerfile
FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install cryptofeed qlib pandas pyarrow requests
CMD ["/bin/bash", "start.sh"]
```

```bash
# start.sh
#!/bin/bash
python get_top50.py
python okx_data_collector.py &  # 后台运行
python convert_to_qlib.py
```

```bash
# crontab
0 0 * * * cd /app && python convert_to_qlib.py  # 每天合并
```

---

## 三、Qlib 策略中使用

```python
import qlib
from qlib.constant import RegCN
from qlib.contrib.model.gbdt import LGBModel
from qlib.workflow import R

qlib.init(provider_uri='/path/to/qlib_data', region=RegCN)

# 直接使用你的数据
instruments = ['BTCUSDT', 'ETHUSDT', ...]
dataset = D.features(instruments, ['$close', '$volume', 'open', 'high', 'low'])
```

---

## 四、优化建议

| 功能 | 建议 |
|------|------|
| **去重** | Parquet 按 `symbol+timestamp` 去重 |
| **容错** | 使用 `supervisor` 或 `systemd` 守护进程 |
| **监控** | 记录日志 + Prometheus 导出采集延迟 |
| **扩展** | 支持多时间粒度（1m/5m/1h）并行采集 |

---

## 五、总结：你现在可以

1. 运行 `get_top50.py` → 获取资金费率前50币种
2. 启动 `okx_data_collector.py` → 实时采集 K 线
3. 每天运行 `convert_to_qlib.py` → 自动生成 Qlib 数据
4. 在 Qlib 中直接回测策略

---
 