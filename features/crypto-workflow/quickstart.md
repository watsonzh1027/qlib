# Crypto Trading Workflow Quickstart Guide

## Prerequisites
```bash
pip install ccxt lightgbm pandas numpy pytest
```

## Data Collection
```bash
# Collect 15-minute OHLCV data for BTC-USDT
python examples/collect_okx_ohlcv.py \
  --symbol BTC-USDT \
  --interval 15min \
  --start 2024-01-01 \
  --end 2024-01-31 \
  --output data/raw/okx/BTC-USDT/15min/
```

## Feature Generation
```bash
# Preprocess raw data and generate features
python examples/preprocess_features.py \
  --input data/raw/okx/BTC-USDT/15min/ \
  --output features/BTC-USDT/15min/v1/ \
  --start 2024-01-01 \
  --end 2024-01-31
```

## Model Training
```bash
# Train LightGBM model
python examples/train_lgb.py \
  --features features/BTC-USDT/15min/v1/ \
  --model-output models/BTC-USDT/15min/v1.bin \
  --train-start 2024-01-01 \
  --train-end 2024-01-25 \
  --val-start 2024-01-26 \
  --val-end 2024-01-31
```

## Signal Generation
```bash
# Generate trading signals
python examples/predict_and_signal.py \
  --model models/BTC-USDT/15min/v1.bin \
  --data features/BTC-USDT/15min/v1/ \
  --output signals/BTC-USDT/15min/v1/
```

## Backtesting
```bash
# Run backtest
python examples/backtest.py \
  --signals signals/BTC-USDT/15min/v1/ \
  --market-data data/raw/okx/BTC-USDT/15min/ \
  --output backtest/BTC-USDT/15min/v1/report.json
```

## Directory Structure
```
qlib/
├── data/
│   └── raw/
│       └── okx/
│           └── BTC-USDT/
│               └── 15min/
├── features/
│   └── BTC-USDT/
│       └── 15min/
├── models/
├── signals/
└── backtest/
```

## Configuration
Key parameters are defined in `config_defaults.yaml`:
- Data collection: rate limits, retry policy
- Feature generation: technical indicators, window sizes
- Model: LightGBM parameters, validation thresholds
- Trading: signal thresholds, position sizing
- Backtest: transaction costs, slippage assumptions
