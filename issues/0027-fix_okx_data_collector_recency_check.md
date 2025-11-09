# Issue 0027: OKX Data Collector Always Downloads Data

## Status: CLOSED
## Created: 2025-11-08 22:31:00

## Problem Description
The OKX crypto data collector was always downloading data from the API regardless of whether local data was recent enough. This caused unnecessary API calls and poor performance, especially when running frequent data collection jobs.

## Root Cause Analysis
The recency check logic in `calculate_fetch_window()` had two critical flaws:

1. **Incorrect timestamp comparison**: The logic compared `end_time` with `last_timestamp` instead of comparing current time with last timestamp
2. **Empty end_time handling**: Empty end_time strings (indicating "latest data") weren't properly handled, causing parsing failures
3. **CSV parsing errors**: The CSV reader functions were reading from the wrong column index (column 1 instead of 0 for timestamps)

## Solution Implemented
Fixed the recency check logic in `scripts/okx_data_collector.py`:

1. **Corrected recency comparison**: Changed from `(end_time - last_timestamp) <= overlap_delta` to `(current_time - last_timestamp) <= overlap_delta`
2. **Fixed empty end_time**: Added handling to treat empty end_time as `pd.Timestamp.now()` for "latest data" requests
3. **Fixed CSV parsing**: Corrected `get_last_timestamp_from_csv()` and `get_first_timestamp_from_csv()` to read timestamp from column 0 instead of 1

## Code Changes
- Modified `calculate_fetch_window()` to use proper current_time comparison
- Added debug logging to show time differences and skip decisions
- Fixed CSV column indexing in timestamp reading functions

## Testing Results
- All symbols now correctly skip API calls when local data is within 5-minute recency threshold
- Debug output shows proper time calculations: `time_diff=0.6 minutes`, `overlap_delta=0 days 00:05:00`, `data_is_recent=True`
- No unnecessary API calls are made when data is fresh

## Performance Impact
- Eliminates redundant API calls for recent data
- Reduces network overhead and API rate limiting issues
- Improves overall data collection performance

## Files Modified
- `scripts/okx_data_collector.py`: Fixed recency logic and CSV parsing

## Validation
✅ All symbols skip downloads when data is recent
✅ No API calls made for fresh data
✅ Debug logging confirms correct time calculations
✅ Incremental collection works as intended