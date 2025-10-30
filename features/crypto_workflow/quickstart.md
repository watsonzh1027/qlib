# Crypto Workflow Quickstart

This quickstart shows example commands for the end-to-end flow: collect → preprocess → train → predict → backtest.

## Prerequisites
- Python 3.9+ and dev environment activated (e.g. conda env named `qlib`)
- ccxt configured for OKX (API key/secret) if doing live collection
- project root is /home/watson/work/qlib

## Example commands (dry-run / test-mode friendly):

### 1) Collect OHLCV (dry-run / short range)
- Dry-run (no API keys, mocked fetch):
  ```bash
  python examples/collect_okx_ohlcv.py \
    --symbol BTC/USDT \
    --timeframe 1h \
    --start 2025-01-01 \
    --end 2025-10-01 \
    --output data/ohlcv/btc_1h.parquet
  ```

- Real run (with OKX keys in env):
  ```bash
  export OKX_API_KEY=xxxx
  export OKX_API_SECRET=yyyy
  python examples/collect_okx_ohlcv.py \
    --symbol BTC/USDT \
    --timeframe 1h \
    --start 2024-01-01 \
    --end 2024-02-01 \
    --output data/ohlcv/btc_1h.parquet
  ```

### 2) Preprocess features
- Run featurization (align, fill, compute MA/RSI):
  ```bash
 python examples/preprocess_features.py \
      --ohlcv-path data/ohlcv/btc_1h.parquet  \
           --symbol btc     \
           --timeframe 1h     \
           --target-path data/features
  ```

### 3) Train LightGBM model (dry-run with small dataset)
- Train and save model + report:
  ```bash
python examples/train_lgb.py --features data/features/features_btc_1h.parquet \
  --model-out models/btc_lgb.pkl \
  --report-out reports/train_btc.json


  ```

### 4) Predict & generate signals
- Load model and generate signals:
  ```bash
  python examples/predict_and_signal.py \
    --model-path models/btc_lgb.pkl \
    --features-path data/features/features_btc_1h.parquet \
    --output-path signals/btc_signals.parquet
  ```

- Use config for thresholds:
  ```bash
    python examples/predict_and_signal.py \
    --model-path models/btc_lgb.pkl \
    --features-path data/features/features_btc_1h.parquet \
    --output-path signals/btc_signals.parquet\
    --config cfg/signal_thresholds.yaml
  ```

### 5) Backtest
- Run backtest using OHLCV + signals:
  ```bash
  python examples/backtest.py \
    --signals signals/btc_signals.parquet \
    --ohlcv data/ohlcv/btc_1h.parquet \
    --output reports/backtest_btc \
    --slippage 0.0005 \
    --fee 0.00075
  ```

## Notes and tips
- Use `--dry-run` or small time ranges for quick smoke tests.
- Store API keys in environment variables (OKX_API_KEY, OKX_API_SECRET) or use a secrets manager — do NOT commit keys.
- For CI/tests, mock exchange calls (see tests/) to avoid external network calls.
- Output locations: data/, models/, reports/, signals/ under repo root by default.

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
