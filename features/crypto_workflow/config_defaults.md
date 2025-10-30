# Crypto Workflow Configuration Defaults

This file documents default paths, naming conventions, timezones and operational defaults used by the crypto workflow.

Paths and file layout
- data/ohlcv/ : raw OHLCV parquet files (per symbol/timeframe)
- data/features/ : featurized parquet files consumed by training/prediction
- models/ : persisted model artifacts (.pkl, .joblib)
- signals/ : generated signals parquet files
- reports/ : training/backtest reports and HTML visualizations

Time & timezone
- Default timezone: UTC
- All timestamps saved as timezone-aware UTC datetime
- Default timeframe examples: 1m, 5m, 15m, 1h, 1d

Model naming conventions
- Model filename format: <symbol>__<model_type>__<YYYYMMDD>.pkl
  e.g. BTC-USDT__lgb__20240115.pkl

Model persistence & atomic write
- Model save/load uses joblib/pickle with atomic write (temp file + rename)
- Metadata (schema, hyperparams) stored alongside model as .json

Collector defaults & retry policy
- Default fetch limit per request: 100
- Retries: 3 attempts on rate-limit / transient errors
- Backoff: exponential backoff base 5s (5s, 10s, 20s)
- Dry-run mode: when enabled, collector will simulate fetches or use cached fixtures

Signal thresholds (defaults)
- buy threshold: 0.7
- sell threshold: 0.3
- max_position: 1.0

Backtest defaults
- Slippage: 0.0005 (0.05%)
- Fee: 0.00075 (0.075%)
- Init capital: 1.0 (normalized)
- Trade sizing: position_size in signals is fraction of portfolio to allocate

Testing & CI
- Tests should not call external exchanges (mock ccxt in tests)
- Use small synthetic datasets for smoke tests to ensure speed in CI

Notes
- Override defaults via CLI args or small YAML config files when available.
- Ensure API keys are provided via environment variables (do not store keys in repo).
