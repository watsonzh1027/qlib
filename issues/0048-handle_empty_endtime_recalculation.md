# Issue: Handle Empty Endtime by Recalculating to Current Time

## Status: CLOSED
## Created: 2025-11-16 00:27:12

## Problem Description
When the `endtime` parameter is empty or None in the data collection process, the system should dynamically recalculate it to the current time (`now`) to ensure collection of the latest available data. Previously, empty endtime values were handled inconsistently, potentially missing recent market data.

## Root Cause
- Empty or None `endtime` parameters were not being recalculated during the data collection process
- The system relied on static endtime values set at function initialization
- This could result in missing recent market data when collecting incremental updates

## Solution Implemented
Added dynamic endtime recalculation logic in the `update_latest_data()` function:

```python
# Convert symbol-specific times to timestamps
# 如果endtime为空或接近当前时间，在开始获取数据时重新计算为当前时间
current_time = pd.Timestamp.now(tz='UTC')
if not symbol_end_time or symbol_end_time.strip() == '' or pd.Timestamp(symbol_end_time, tz='UTC') >= current_time:
    symbol_end_time = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.debug(f"Recalculated end_time to current time for {symbol}: {symbol_end_time}")
```

## Changes Made
1. Added endtime validation and recalculation logic before timestamp conversion (lines 907-911)
2. Checks for empty, whitespace-only, or future endtime values
3. Automatically recalculates to current UTC time when conditions are met

## Testing Results
- ✅ **Functionality test**: PASSED - Empty endtime correctly recalculated to current time
- ✅ **Data collection**: PASSED - Successfully collected data with dynamic endtime
- ✅ **No regressions**: Existing functionality preserved for valid endtime values

## Performance Impact
- **Minimal overhead**: Only adds timestamp comparison and formatting when endtime needs recalculation
- **Improved data freshness**: Ensures latest market data is always collected when endtime is unspecified
- **Better user experience**: No manual intervention required for collecting up-to-date data

## Files Modified
- `scripts/okx_data_collector.py`: Added dynamic endtime recalculation in `update_latest_data()` function

## Validation
Tested with empty endtime parameter - confirmed automatic recalculation to current time and successful data collection.