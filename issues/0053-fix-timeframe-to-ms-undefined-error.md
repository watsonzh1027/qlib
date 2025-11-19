# Issue: Fix undefined 'timeframe_to_ms' function error in data collector

## Status: CLOSED
## Created: 2025-11-18 23:00:00

## Problem Description
The OKX data collector was failing with "name 'timeframe_to_ms' is not defined" error when encountering empty API responses. This occurred when the collector tried to skip to the next timeframe slot after getting empty responses from the exchange.

## Root Cause
The `timeframe_to_ms` function was referenced in the code (line 966) but never defined. This function is used to convert timeframe strings (like '1h') to milliseconds for timestamp calculations when handling empty API responses.

## Solution Steps
1. Added `timeframe_to_ms(timeframe: str) -> int` function that converts timeframe strings to milliseconds:
   - '1m' → 60 * 1000 = 60,000 ms
   - '15m' → 15 * 60 * 1000 = 900,000 ms  
   - '1h' → 60 * 60 * 1000 = 3,600,000 ms
   - '1d' → 24 * 60 * 60 * 1000 = 86,400,000 ms
   - Default: 60,000 ms (1 minute)

## Final Result
Data collection now handles empty API responses correctly by properly incrementing timestamps. The collector can continue fetching data even when encountering temporary gaps in exchange data availability.

## Files Modified
- `scripts/okx_data_collector.py`: Added timeframe_to_ms function

## Testing Results
Ran test command to verify the fix:
```bash
timeout 30 python scripts/okx_data_collector.py --output db --start_time 2025-11-01T00:00:00Z --end_time 2025-11-02T00:00:00Z
```

**Result:** Data collection proceeds without errors. The undefined function error is resolved and BTC/USDT data is being collected successfully (39,000+ candles collected before timeout).</content>
<parameter name="filePath">/home/watson/work/qlib-crypto/issues/0053-fix-timeframe-to-ms-undefined-error.md