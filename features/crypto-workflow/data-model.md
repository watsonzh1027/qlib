# data-model.md — Entities for crypto workflow

## Entities

1. RawOHLCV
   - Fields: exchange, symbol, interval, timestamp (ms UTC), open, high, low, close, volume, source_file, fetched_at
   - Validation: timestamps monotonic per file; no negative prices/volumes; required fields present

2. ProcessedOHLCV
   - Fields: same as RawOHLCV + adjusted_close, fills (bool), gap_flag
   - Validation: aligned to interval boundary; missing filled with forward/backfill policy; gap_flag if > threshold

3. FeatureSet
   - Fields: feature_id, symbol, interval, window_length, features (dict or columns), label (e.g., next_return>threshold)
   - Validation: feature columns present, no NaN after featurization (or documented imputation)

4. ModelArtifact
   - Fields: model_id, model_version, algorithm (LightGBM), feature_schema, training_period, metrics, path
   - Validation: model file exists at path; metrics present

5. Signal
   - Fields: timestamp, symbol, model_id, signal (BUY/SELL/HOLD), score, confidence, position_size
   - Validation: timestamps within market hours; position sizing <= max_allowed

6. BacktestResult
   - Fields: model_id, timeseries (equity_curve), trades (list), metrics (sharpe, max_drawdown, return, win_rate), assumptions
   - Validation: metrics computed and stored; trades reconcile with signals

## File layout (recommended)
- data/raw/okx/{symbol}/{interval}/{YYYYMMDD}.parquet
- data/processed/{symbol}/{interval}/{version}.parquet
- features/{feature_set}/{train|val}.parquet
- models/{model_id}/{model_version}.bin
- signals/{model_id}/{date}.csv
- backtest/{model_id}/{model_version}/report.json
