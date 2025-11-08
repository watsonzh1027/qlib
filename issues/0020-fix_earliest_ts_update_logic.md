# Issue 0020: Fix earliest_ts update logic in update_latest_data

**Status:** CLOSED  
**Created:** 2025-11-05 21:30:00  

## Problem Description
The `update_latest_data` function in `scripts/okx_data_collector.py` had a logic flaw where `earliest_ts` was being updated with timestamps from API responses even when those timestamps were outside the requested time range. This caused the function to continue making API requests with the same `before` parameter, leading to infinite loops or repeated requests for the same data.

## Root Cause
In the candle processing loop, the code was updating `earliest_ts` outside the time range check:

```python
if ts_ms <= end_ts:  # Within range
    processed_candles.append({...})

if ts_ms < earliest_ts:  # This was outside the range check!
    earliest_ts = ts_ms
```

When the OKX API returned recent data that was outside the requested time range, `earliest_ts` would still be set to those timestamps, causing the pagination logic to continue requesting the same data.

## Solution
Moved the `earliest_ts` update inside the time range check so it only gets updated when candles are actually within the requested time range:

```python
if ts_ms <= end_ts:  # Within range
    processed_candles.append({...})
    if ts_ms < earliest_ts:  # Now inside the range check
        earliest_ts = ts_ms
```

## Testing
- Verified that the function now correctly stops when API returns data outside the time range
- Confirmed no infinite loops occur when requesting historical data that doesn't exist
- Function properly handles OKX API limitations where only recent data is available

## Files Modified
- `scripts/okx_data_collector.py`: Fixed earliest_ts update logic in update_latest_data function

## Validation
The fix was tested with a time range that should return no data (due to API limitations), and the function correctly stopped after one request instead of entering an infinite loop.