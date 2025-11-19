# Issue: Fix PostgreSQL partition subpartitioning and timezone issues in convert_to_qlib.py

## Status: CLOSED
## Created: 2025-11-18 22:02:00

## Problem Description
The data collector successfully fetched and attempted to save 61807 candles for BTC/USDT to PostgreSQL, but failed with "no partition of relation 'ohlcv_data_1h' found for row" due to subpartitioning by timestamp range not being created. Additionally, the convert_to_qlib.py script failed with timezone conversion errors when processing timezone-aware timestamps from the database.

## Root Cause
1. PostgreSQL partitioned table setup created subpartitions by RANGE (timestamp), but no actual range partitions were created, causing inserts to fail.
2. For crypto data (24/7 trading), calendar alignment is unnecessary and caused timezone issues with tz-aware timestamps.
3. Filename generation for database-loaded symbols included '/' which was interpreted as path separators.

## Solution Steps
1. Modified `postgres_config.py` to remove subpartitioning by RANGE (timestamp) for crypto data, keeping only LIST partitioning by interval.
2. Updated `convert_to_qlib.py` `_data_to_bin_crypto` to skip calendar merging for crypto data and handle tz-aware timestamps directly.
3. Fixed filename generation by replacing '/' with '_' in symbol names for CSV export.
4. Recreated database schema with `--drop-existing` to apply partition changes.

## Final Result
- Data collector now successfully saves OHLCV data to PostgreSQL partitions.
- convert_to_qlib.py processes database data and converts to Qlib binary format without timezone errors.
- Total of 30 feature files created for the test data (5 OHLCV fields × 6 time intervals, though only 1h data was loaded).

## Files Modified
- `scripts/postgres_config.py`: Removed subpartitioning by range for crypto partitions
- `scripts/convert_to_qlib.py`: Updated crypto data saving to skip calendar alignment, fixed filename handling