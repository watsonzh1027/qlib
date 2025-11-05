# Spec: Data Collection Capability (change 0001)

## Why
The purpose of this change is to introduce a robust data collection capability to support trading strategies and analytics. This ensures:
- Accurate and timely data collection from OKX perpetual swaps.
- Efficient storage and processing of OHLCV data.
- On-demand updates for flexibility in data retrieval.
- Compatibility with the Qlib framework for feature generation and analysis.

## ADDED Requirements

### Requirement: Top-50 Symbol Selection
- The system MUST fetch funding rates for OKX perpetual swaps via CCXT REST.
- The system MUST rank symbols by absolute funding rate and produce a top-50 list.
- The top-50 list MUST be saved as `config/instruments.json` with fields: symbols, funding_rate, updated_at (ISO8601), count.

#### Scenario: Generate top-50
- Given OKX REST is reachable,
- When `get_okx_funding_top50()` is invoked,
- Then it returns a list of 50 symbols sorted by decreasing absolute funding rate and writes `config/instruments.json`.

### Requirement: Persist OHLCV and Funding Rate Data
- The collector MUST save OHLCV candles for each tracked symbol into `data/klines/{symbol}/{symbol}_{interval}.parquet`.
- The collector MUST save funding rate data into `data/funding/funding_rates_{date}.parquet`.
- Each row in OHLCV data MUST include: symbol, timestamp (unix seconds), open, high, low, close, volume, interval.
- Each row in funding rate data MUST include: symbol, timestamp (unix seconds), funding_rate, predicted_rate.

#### Scenario: Append new OHLCV and funding rate data
- Given new OHLCV and funding rate data are available for a tracked symbol,
- When the collector flushes buffer,
- Then rows with correct timestamps and values are appended to the respective Parquet files.

### Requirement: Qlib Conversion
- The converter MUST scan `data/klines/{symbol}/*.parquet`, merge per-symbol data, dedupe, and produce Qlib-compatible artifacts:
  - `data/qlib_data/instruments/all.txt` and binary feature files.
- The converter MUST ensure no gaps in data and correct timestamps.

#### Scenario: Convert to Qlib format
- Given OHLCV data exists in `data/klines/`,
- When `convert_to_qlib()` runs,
- Then Qlib-compatible data is generated in `data/qlib_data/`.

### Requirement: Centralized Parameter Management
- The system MUST use a centralized configuration file (`config/workflow.json`) to store parameters for data collection, conversion, and backtesting.
- The `ConfigManager` module MUST provide default values for missing parameters and ensure consistency across scripts.

#### Scenario: Load parameters dynamically
- Given `config/workflow.json` exists,
- When `ConfigManager` is invoked,
- Then it loads parameters dynamically and provides defaults for missing values.

## Validation
- Unit tests MUST exist for:
  - Top-50 selection logic
  - OHLCV and funding rate persistence
  - Qlib conversion logic
  - ConfigManager parameter loading
- Integration smoke tests MUST verify Qlib can load converted data.

