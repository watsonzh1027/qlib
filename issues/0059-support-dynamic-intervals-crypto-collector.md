# Issue: Support Dynamic Intervals in Crypto Data Collector

## Description
The previous implementation used hardcoded constants like `INTERVAL_1d` and specific subclasses like `CryptoCollector1d`, which made it difficult to support a wide range of intervals (e.g., 5min, 15min, 30min, 1h, 4h, 1w).

## Changes
- Refactored `CryptoCollector` and `CryptoNormalize` into generic classes that handle intervals dynamically.
- Removed hardcoded constants and specific subclasses (`CryptoCollector1h`, etc.) in favor of a single implementation.
- Updated `timeframe_map` in `get_data_from_remote` to support CCXT timeframes: `1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w`.
- Overrode `normalize_start_datetime` and `normalize_end_datetime` in `CryptoCollector` to provide safe defaults for any interval string.
- Simplified `Run` class to return generic class names for collection and normalization.
- Updated unit tests to cover multiple intervals and adapted to the new architecture.

## Verification Results
- Ran `python -m unittest tests/test_crypto_collector.py`
- All 16 tests passed.
- Verified support for `1h` interval as requested by the user.

## Status
CLOSED
