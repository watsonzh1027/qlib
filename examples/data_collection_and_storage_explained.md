# Qlib 数据采集与存储深度解析

本文档旨在详细解释 `Qlib` 库中关于金融数据（特别是K线）的采集、处理和本地存储的原理与过程，并提供针对加密货币等自定义数据的采集方案。

## 1. Qlib 数据体系核心原理

`Qlib` 的设计哲学是将数据与算法解耦。为了实现高效的AI量化研究，`Qlib` 构建了一套高性能的本地数据存储和访问方案。其核心原理如下：

*   **二进制存储**: 传统数据库（如MySQL）或文本文件（CSV）在读取大量金融时间序列数据时，会涉及大量的I/O和数据解析开销。`Qlib` 选择将数据处理成特定的二进制格式（`.bin` 文件），这使得数据能够被极快地加载到内存中，特别是与 `numpy` 等科学计算库结合使用时，可以实现接近内存访问的速度。
*   **目录结构化**: `Qlib` 规定了一套标准的数据目录结构，将不同类型的数据分门别类地存储。一个典型的数据目录（例如 `~/.qlib/qlib_data/cn_data`）包含：
    *   `calendars/`: 交易日历文件（如 `day.txt`），定义了交易的日期序列。
    *   `instruments/`: 股票列表文件（如 `all.txt`, `csi300.txt`），定义了股票池。
    *   `features/`: 存放核心K线数据的地方。每个股票代码对应一个目录（如 `sh600000`），目录下存放着不同特征的 `.bin` 文件（如 `close.bin`, `open.bin`, `high.bin`, `low.bin`, `volume.bin`, `factor.bin` 等）。
*   **数据提供者 (Provider)**: `Qlib` 通过 `qlib.init()` 初始化，其中 `provider_uri` 参数指定了数据存储的路径。`Qlib` 会根据这套标准结构来加载和查询数据。这种设计使得用户可以轻松切换不同的数据集，只需指向不同的数据目录即可。
*   **可扩展的数据采集器**: `Qlib` 提供了一个基础的数据采集器框架（`data_collector.base`），允许用户方便地自定义数据源。项目 `scripts/data_collector/` 目录下的 `yahoo` 采集器就是一个很好的例子，它负责从雅虎财经获取股票数据并转换为 `Qlib` 的二进制格式。

## 2. `GetData().qlib_data` 背后过程解析

在 `examples/workflow_by_code.py` 等多个示例文件中，我们都能看到如下代码：

```python
from qlib.tests.data import GetData

# ...
provider_uri = "~/.qlib/qlib_data/cn_data"
GetData().qlib_data(target_dir=provider_uri, region=REG_CN, exists_skip=True)
qlib.init(provider_uri=provider_uri, region=REG_CN)
```

这里的 `GetData().qlib_data` 并不是一个实时的数据采集过程，而是一个 **“便利的数据集下载和解压工具”**。

它的具体工作流程如下：

1.  **定位与封装**: `GetData` 类位于 `qlib.tests.data` 模块，它本质上是对 `scripts/get_data.py` 脚本的Python函数式封装，目的是方便在代码中直接调用，而无需通过命令行。

2.  **检查目标目录**: `exists_skip=True` 参数会使函数首先检查 `target_dir` (即 `~/.qlib/qlib_data/cn_data`) 是否已经存在数据。如果存在，则跳过后续步骤，避免重复下载。

3.  **下载预打包数据**: 如果目标目录不存在或为空，该函数会从一个预设的URL下载一个已经打包好的数据集（通常是 `.tar.gz` 或 `.zip` 文件）。这些数据集是 `Qlib` 官方或社区预先通过数据采集器（如 `yahoo` 采集器）生成并打包上传的。
    > 正如项目 `README.md` 中提到的，由于数据安全策略，官方下载源可能不稳定，社区提供了备用下载链接。`get_data.py` 脚本内部维护了这些下载地址。

4.  **解压到指定位置**: 下载完成后，脚本会将压缩包解压到 `target_dir` 目录，并按照 `Qlib` 标准的目录结构（`calendars/`, `instruments/`, `features/`）进行组织。

**总结**: `GetData().qlib_data` 是一个“一键安装”官方/社区预制数据集的快捷方式，它让用户可以跳过复杂的数据采集和处理步骤，快速开始使用 `Qlib`。它下载的是历史数据的快照，而不是实时数据。如果需要最新的数据，用户需要运行 `scripts/data_collector/yahoo/collector.py` 中的更新命令来增量更新。

## 3. 加密货币（Crypto）数据采集方案

`Qlib` 的框架完全支持自定义数据源，包括加密货币。要实现Crypto数据的采集，可以遵循以下步骤，创建一个自定义的数据采集器：

#### 步骤 1: 选择数据源

选择一个提供加密货币历史K线数据的API。常见的可靠数据源包括：
*   **交易所官方API**: Binance, Coinbase, OKX 等都提供公开的K线数据API。
*   **第三方数据提供商**: CCXT（一个流行的开源库，集成了上百家交易所的API）、CoinAPI、Kaiko 等。

推荐使用 **CCXT** 库，因为它封装了多家交易所的接口，代码可移植性好。

#### 步骤 2: 创建自定义采集器

参考 `scripts/data_collector/yahoo` 的结构，在 `scripts/data_collector/` 目录下创建一个新的文件夹，例如 `crypto_collector`。

在该文件夹下，创建一个 `collector.py` 文件，并实现以下几个关键部分：

1.  **安装依赖**:
    ```bash
    pip install ccxt pandas
    ```

2.  **实现 `Collector` 类**:
    这个类负责从API获取原始数据并将其格式化为 `pandas.DataFrame`。

    ```python
    # In scripts/data_collector/crypto_collector/collector.py
    import ccxt
    import pandas as pd
    from datetime import datetime
    from qlib.data.collector.base import BaseCollector

    class CryptoCollector(BaseCollector):
        def __init__(
            self,
            start="2020-01-01",
            end=None,
            interval="1d",
            max_retries=5,
            symbol_list=None,
            exchange_name="binance", # e.g., binance, coinbase
        ):
            super().__init__(start, end, interval, max_retries)
            self.exchange = getattr(ccxt, exchange_name)()
            self.symbol_list = symbol_list or ["BTC/USDT", "ETH/USDT"]

        def get_data(self, symbol, interval, start, end):
            """
            Fetch data for a single symbol.
            """
            start_ts = int(self.start.timestamp() * 1000)
            limit = 1000  # Most exchanges have a limit per request
            all_ohlcv = []

            while start_ts < int(datetime.now().timestamp() * 1000):
                try:
                    ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=interval, since=start_ts, limit=limit)
                    if not ohlcv:
                        break
                    all_ohlcv.extend(ohlcv)
                    new_start_ts = ohlcv[-1][0] + 1
                    if new_start_ts == start_ts: # No new data
                        break
                    start_ts = new_start_ts
                except Exception as e:
                    print(f"Error fetching {symbol}: {e}")
                    break
            
            if not all_ohlcv:
                return pd.DataFrame()

            df = pd.DataFrame(all_ohlcv, columns=["datetime", "open", "high", "low", "close", "volume"])
            df["datetime"] = pd.to_datetime(df["datetime"], unit="ms")
            df = df.set_index("datetime")
            
            # Format for Qlib
            df = df.rename(columns={"open": "OPEN", "high": "HIGH", "low": "LOW", "close": "CLOSE", "volume": "VOLUME"})
            df["SYMBOL"] = symbol.replace("/", "") # e.g., BTCUSDT
            df.index.name = "DATE"
            return df[~df.index.duplicated(keep='first')] # Remove duplicates

        def get_all_data(self):
            """
            Fetch data for all symbols in the list.
            """
            all_df = []
            for symbol in self.symbol_list:
                print(f"Fetching data for {symbol}...")
                df = self.get_data(symbol, self.interval, self.start, self.end)
                if not df.empty:
                    all_df.append(df)
            return pd.concat(all_df)
    ```

3.  **实现数据规范化和存储**:
    在同一个文件中，实现 `Normalize` 和 `Run` 类，它们负责调用 `Collector`，处理数据（如计算复权因子，对于Crypto通常为1），并使用 `qlib` 的工具将DataFrame写入二进制文件。可以大量复用 `qlib.data.collector.base` 和 `qlib.data.collector.utils` 中的功能。

#### 步骤 3: 运行采集器

完成采集器脚本后，通过命令行运行它，将数据下载并存储到指定的目录：

```bash
python scripts/data_collector/crypto_collector/collector.py dump_all --csv_path <your_temp_csv_path> --qlib_dir ~/.qlib/qlib_data/crypto_data --include_fields open,high,low,close,volume
```

#### 步骤 4: 在 Qlib 中使用

数据准备好后，就可以在 `qlib` 中初始化并使用了：

```python
import qlib

provider_uri = "~/.qlib/qlib_data/crypto_data"
# For crypto, region is not a standard concept, so we can ignore it or use a custom one.
qlib.init(provider_uri=provider_uri)

# Now you can use D.features() to load crypto data
from qlib.data import D

df = D.features(instruments=["BTCUSDT", "ETHUSDT"], fields=["$close", "$volume"])
print(df.head())
```

通过以上步骤，您就可以将加密货币数据无缝集成到 `Qlib` 的研究工作流中，利用其强大的模型和回测引擎进行策略开发。