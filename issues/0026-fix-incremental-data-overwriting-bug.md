# Issue 0026: Fix incremental data collection overwriting bug

## Status: CLOSED
## Created: 2025-11-07 21:45:00

## Problem Description
The incremental data collection feature was overwriting existing CSV data instead of appending new data. This was caused by a bug in the `save_klines` function where datetime timestamps were being corrupted during the save process, leading to data loss.

## Root Cause Analysis
1. **Timestamp Type Mismatch**: The `save_klines` function was not properly handling mixed timestamp types (int vs datetime) in the DataFrame
2. **Datetime Corruption**: When saving, the function was converting timestamps incorrectly, causing existing data to be overwritten instead of merged
3. **Merge Logic Flaw**: The merging process wasn't preserving existing data when new data was added

## Solution Implemented
1. **Fixed Timestamp Handling**: Modified `save_klines` to properly handle both int and datetime timestamp columns
2. **Conditional Conversion**: Added logic to only convert timestamps when necessary, preserving existing datetime format
3. **Verified Merge Logic**: Confirmed that `update_latest_data` correctly merges new data with existing data using `drop_duplicates` and proper sorting

## Testing Results
- **Before Fix**: BTC_USDT had 3 lines (header + 2 data rows)
- **After Fix**: BTC_USDT has 84 lines (header + 83 data rows)
- **Data Integrity**: All timestamps are properly formatted as datetime strings
- **Incremental Behavior**: New data was correctly appended starting from the last existing timestamp
- **Multi-Symbol Support**: All configured symbols (BTC_USDT, ETH_USDT, etc.) received incremental updates

## Code Changes
- `scripts/okx_data_collector.py`: Fixed `save_klines` function to handle timestamp types correctly
- Verified `update_latest_data` function properly merges data without overwriting

## Validation Steps
1. Checked existing data before running script
2. Ran incremental collection with limit=5
3. Verified line count increased from 3 to 84
4. Confirmed timestamps are sequential and properly formatted
5. Checked multiple symbols have data collected

## Impact
- ✅ Incremental data collection now works correctly
- ✅ No data loss during updates
- ✅ API calls are minimized through proper incremental fetching
- ✅ All configured symbols receive updates
- ✅ Data integrity maintained with proper timestamp handling

## Lessons Learned
- Always validate timestamp handling in pandas operations
- Test merge operations thoroughly to prevent data loss
- Use conditional type conversion to preserve data formats
- Verify incremental behavior with before/after data checks