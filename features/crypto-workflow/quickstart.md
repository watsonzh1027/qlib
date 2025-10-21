# quickstart.md — End-to-end example (local)

1. 拉取 1 天的分钟线 OHLCV（示例）
   - 调用脚本： `python examples/collect_okx_ohlcv.py --symbol BTC/USDT --interval 1m --since 2025-01-01`
   - 输出： `data/raw/okx/BTC-USDT/1m/{YYYYMMDD}.parquet`

2. 数据清洗与特征生成
   - 调用脚本： `python examples/preprocess_features.py --input data/raw/... --output data/processed/...`
   - 输出： `data/processed/BTC-USDT/1m/v1.parquet` 和 `features/feature_set/train.parquet`

3. 训练模型（LightGBM）
   - 调用脚本： `python examples/train_lgb.py --features features/feature_set/train.parquet --out models/feature_set/v1.bin`
   - 输出： 模型文件 `models/feature_set/v1.bin` 和评估报告 `reports/train/v1/`

4. 加载模型并预测、生成信号
   - 调用脚本： `python examples/predict_and_signal.py --model models/feature_set/v1.bin --input data/processed/... --out signals/feature_set/v1/2025-01-09.csv`

5. 回测
   - 调用脚本： `python examples/backtest.py --signals signals/... --ohlcv data/raw/... --out backtest/feature_set/v1/report.json`
   - 输出： 回测报告 JSON 与交易明细 CSV

注意：
- 每一步都有可配置参数（交易对、时间粒度、手续费、滑点）。
- 保持 manifest 文件以记录数据/模型的版本与起止时间，便于复现。
