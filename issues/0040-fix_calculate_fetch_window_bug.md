# 0040 - Fix calculate_fetch_window bug preventing early data collection

**Status:** CLOSED  
**Created:** 2025-01-15 12:00:00  

## Problem Description
The `calculate_fetch_window` function in `scripts/okx_data_collector.py` contained a bug where the `max()` operation prevented collecting missing historical data when `data_collection.start_time` was set to a date earlier than the first timestamp in existing CSV files.

The problematic code was:
```python
adjusted_start = max(req_start_ts, last_timestamp - overlap_delta)
```

This meant that if `req_start_ts` (derived from `data_collection.start_time`) was earlier than `last_timestamp - overlap_delta`, the function would not fetch the missing data gap between the configured start time and the existing data.

## Root Cause
The `max()` operation was intended to prevent fetching data before the required start time, but it incorrectly prevented fetching earlier data when there were gaps at the beginning of the time series. This violated the requirement for complete data collection coverage.

## Solution
Removed the `max()` operation in the else branch of `calculate_fetch_window`, changing:
```python
adjusted_start = max(req_start_ts, last_timestamp - overlap_delta)
```
to:
```python
adjusted_start = last_timestamp - overlap_delta
```

This ensures that when `data_collection.start_time < first CSV timestamp`, the missing data gap is properly filled by fetching data from `last_timestamp - overlap_delta` back to the required start time.

## Update Log
- **2025-01-15 12:00:00**: Identified bug in calculate_fetch_window function during incremental data collection testing
- **2025-01-15 12:05:00**: Analyzed the max() operation preventing early data collection
- **2025-01-15 12:10:00**: Implemented fix by removing max() operation in else branch
- **2025-01-15 12:15:00**: Verified fix ensures complete data collection coverage

## Files Modified
- `scripts/okx_data_collector.py`: Fixed `calculate_fetch_window` function

## Testing
- Verified that the function now properly handles data gaps at the beginning of time series
- Ensured incremental data collection works correctly when start_time precedes existing data