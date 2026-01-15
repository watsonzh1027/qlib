# Issue: Fix Zero Trades, Implement Hybrid Features, and Enhance Logging

## Description
During the hyperparameter tuning and model evaluation process for the crypto platform, several critical issues were identified and resolved:
1. **Zero Trades Detected**: The backtest was not generating any trades due to data mismatches and missing price adjustment fields in the crypro dataset.
2. **Feature Discrepancy**: The feature set used in `CryptoAlpha158WithFunding` did not align with the hybrid design (Alpha158 + Alpha360 + Custom) required for optimal performance.
3. **Logging Spam**: Subprocesses during tuning were rotating logs on every startup, leading to fragmented and excessive log files.
4. **Calendar Warnings**: Frequent warnings regarding missing `240min` calendars for future predictions.

## Goals
- [x] Resolve the "Zero Trades" issue in backtesting.
- [x] Align `CryptoAlpha158WithFunding` with the hybrid feature design.
- [x] Optimize logging for multi-process environments (grouping by Main PID).
- [x] Resolve calendar and factor-related warnings.

## Solution Detail

### 1. Zero Trades Resolution
- **Instrument Mapping**: Fixed `scripts/run_backtest.py` to correctly map prediction symbols (e.g., `ETHUSDT`) to the Qlib-internal format required by the exchange (e.g., `ETH_USDT_4H_FUTURE`).
- **Dynamic Quote Fields**: Modified `qlib/backtest/exchange.py` to detect missing `$factor` and `$change` fields (standard in stocks but missing in crypto) and inject default values (1.0 and 0.0) to satisfy the executor's tradability checks.

### 2. Hybrid Feature Design
- **Enhanced Handler**: Updated `CryptoAlpha158WithFunding` to include:
    - **Alpha158**: 158 technical indicators.
    - **Alpha360**: 360 price-volume features.
    - **Custom Technicals**: `range`, `vwap_dev`, `rsv10`, and time-based sine/cosine features.
    - **Funding Rate Features**: 9 derived features from funding rate CSV data.
- **Dimensionality**: Total feature count increased to **535**, providing the necessary input width for models like ALSTM.

### 3. Multi-Process Logging Optimization
- **Session Tracking**: Introduced `QLIB_MAIN_PID` environment variable to link subprocesses to the root tuning script.
- **Log Naming**: Subprocess logs now include the main PID (e.g., `qlib-run_backtest-45980-1.log`).
- **Append Mode**: Subprocesses now use `append` mode on startup instead of `rotate`, preventing logs from being reset on every trial.

### 4. Infrastructure Fixes
- **Calendar Mocking**: Created `240min_future.txt` in the calendars directory to suppress warnings when Qlib looks for future timestamps during prediction.

### 5. MultiIndex Consistency FIX
- **Bug Discovery**: Found that merging funding rate features caused the MultiIndex to swap to `(datetime, instrument)`, while Qlib components expect `(instrument, datetime)`.
- **Symptoms**: Strategies were unable to find scores for any instrument, resulting in consistent Zero Trades.
- **Fix**: Added explicit `swaplevel().sort_index()` in `CryptoAlpha158WithFunding.fetch`.

## Verification
- **Unit Test**: `tests/test_crypto_handler.py` verified the 535-dimension hybrid feature output.
- **Index Order Check**: Verified via `tmp/debug_pred.txt` that predictions now follow the correct `(instrument, datetime)` order.
- **Tuning Run**: Trial 17 achieved a WPS score of **2.15** with valid trades.

## Status: IN_PROGRESS
- Re-opened on 2026-01-14 to perform final full-period backtest validation with the index fix.
- Best ETHUSDT params identified.
