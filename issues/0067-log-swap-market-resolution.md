Status: CLOSED
Created: 2026-02-08 00:00:00

# Problem Description
Need to verify whether OKX data collection is using contract (swap/future) markets; current logs do not show resolved market symbols or market type, so it is not possible to confirm from logs.

# Final Solution
- Add a helper to resolve CCXT market symbols based on configured market type and available markets.
- Log market type, ccxt defaultType, resolved market symbol, and selected market info during collection.
- Use the resolved market symbol for OHLCV fetching and availability checks.
- Add unit tests for swap/future and spot symbol resolution.

# Update Log
- Added `resolve_market_symbol()` and integrated it into availability checks and OHLCV fetching.
- Logged market resolution details in `update_latest_data()`.
- Added unit tests for market symbol resolution in `tests/test_okx_data_collector.py`.
- 2026-02-08 22:34:21 Confirmed in logs that collection uses contract market: market_type=future and resolved market_symbol=ETH/USDT:USDT (swap).
