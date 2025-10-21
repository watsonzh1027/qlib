# specify init command:

specify init --here --ai github --ignore-agent-tools

参考 examples/workflow_by_code.py，对 examples/crypto_intraday_demo.py 进行修改， 实现针对 crypto 的 workflow, 完成从数据采集、清洗、训练、模型评价、交易信号产生、回测等一系列流程。

1. 数据采集
   - 将数据源从 CoinGeckoAPI 改为使用 ccxt 拉取 OKX 的 OHLCV 数据（ccxt.fetch_ohlcv）。
   - 将原始 OHLCV 数据按交易对和时间粒度存储到本地文件（推荐 Parquet 或压缩 CSV），文件目录示例：`data/raw/okx/{pair}/{interval}/`.
   - 记录元信息（数据起止时间、exchange、symbol、interval、采集时间）到 manifest 文件。

2. 数据清洗与特征工程
   - 从原始 OHLCV 生成标准化的时间序列（对齐时戳、填充缺失）。
   - 保存清洗后数据到 `data/processed/{pair}/{interval}/`。
   - 导出用于训练的特征集文件（例如 parquet），并记录数据版本。

3. 训练（LGBModel）
   - 使用 LightGBM（LGBModel）做模型训练，训练脚本将读取 processed 特征文件。
   - 将训练好的模型序列化保存到 `models/{feature_set}/{model_version}.bin`（或 joblib/pickle 形式）。
   - 输出训练评估报告到 `reports/train/{model_version}/`.

4. 预测与信号产生
   - 加载本地模型文件到内存，批量或在线预测。
   - 根据模型输出定义买/卖/空/平信号规则并生成 signal 文件到 `signals/{model_version}/{date}.csv`。

5. 回测
   - 使用生成的 signals 与历史 OHLCV 做回测，输出绩效指标与交易明细到 `backtest/{model_version}/`.
   - 回测应包含滑点、费用和资金曲线等基础假设（在 quickstart/contract 里列明）。

输出产物（Phase1）：
- /home/watson/work/qlib/features/crypto-workflow/research.md
- /home/watson/work/qlib/features/crypto-workflow/data-model.md
- /home/watson/work/qlib/features/crypto-workflow/contracts/crypto-api.yaml
- /home/watson/work/qlib/features/crypto-workflow/quickstart.md

实现要点（摘要）：
- 数据采集改用 ccxt + OKX OHLCV，存本地文件。
- 训练使用 LGBModel，模型序列化到本地。
- 模型加载后进行预测、信号产生并回测验证。