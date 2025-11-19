# Issue: Fix data integrity validation interval calculation for crypto data collection

## Status: CLOSED
## Created: 2025-11-18 22:08:00

## Problem Description
The OKX data collector repeatedly collects and saves data to the database, but each time detects that the database records are abnormal, clears them, and re-collects. This creates an infinite loop of data collection.

The issue is that data integrity validation uses incorrect interval_minutes calculation:
- For TIMEFRAME='1h', it was using interval_minutes=1 instead of 60
- This caused the continuity check to flag normal 1-hour gaps as errors

## Root Cause
In `okx_data_collector.py`, the data continuity validation calls used:
```python
interval_minutes=15 if TIMEFRAME == '15m' else 1
```
This only handled '15m' correctly, but for '1h' used 1 minute instead of 60 minutes.

## Solution Steps
1. Added `get_interval_minutes(timeframe: str) -> int` function to properly calculate interval in minutes:
   - '1m' → 1
   - '15m' → 15  
   - '1h' → 60
   - '1d' → 1440

2. Updated all validation calls to use `get_interval_minutes(TIMEFRAME)` instead of hardcoded values.

## Final Result
Data integrity validation now correctly identifies valid crypto data continuity. The collector will no longer falsely detect gaps in 1-hour interval data and clear/re-collect unnecessarily.

## Files Modified
- `scripts/okx_data_collector.py`: Added get_interval_minutes function and updated validation calls

## Testing Results
Ran test command to verify the fix:
```bash
timeout 30 python scripts/okx_data_collector.py --output db --start_time 2025-11-01T00:00:00Z --end_time 2025-11-02T00:00:00Z
```

**Result:** Data integrity validation now passes correctly. Output shows:
```
Database data integrity OK for BTC/USDT
```

Previously, this would have failed with gap detection errors, causing data clearing and re-collection. The fix prevents the infinite collection loop.