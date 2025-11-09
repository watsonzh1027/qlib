# Issue 0028: Fix timestamp parsing error in convert_to_qlib.py

**Status:** CLOSED  
**Created:** 2025-11-08 17:18:00  

## Problem Description
The `convert_to_qlib.py` script failed with `ValueError: non convertible value 2025-11-08 00:15:00 with the unit 's'` because it assumed timestamps in CSV files were Unix timestamps in seconds, but they are actually datetime strings like '2025-11-08 00:15:00'.

## Root Cause
- Code used `pd.to_datetime(..., unit='s')` assuming seconds since epoch.
- CSV data has formatted datetime strings, not numeric timestamps.

## Solution
- Removed `unit='s'` from `pd.to_datetime()` calls in both `validate_data_integrity()` and `convert_to_qlib()` functions.
- Changed to `pd.to_datetime(merged_df['timestamp'])` to auto-parse the string format.

## Steps Taken
1. Identified error in timestamp conversion.
2. Updated `validate_data_integrity` to remove `unit='s'`.
3. Updated `convert_to_qlib` to remove `unit='s'`.
4. Tested script execution - completed successfully with 23 symbols processed.

## Final Solution
Modified lines in `/home/watson/work/qlib-crypto/scripts/convert_to_qlib.py`:
- Line ~35: `df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'])`
- Line ~69: `merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp'])`