# Issue 0046: Fix database column name mismatch in data validation

## Status: OPEN
## Created: 2025-11-15 12:00:00

## Problem Description
Database kline data validation failed due to column name mismatch. The validation query used incorrect column names (`open`, `high`, `low`, `close`) instead of the actual database column names (`open_price`, `high_price`, `low_price`, `close_price`), causing validation to fail and incorrectly clearing existing data for symbols.

## Root Cause
- `validate_database_continuity()` function used wrong column names in SQL query
- Database schema uses `_price` suffix for OHLC columns but validation query didn't account for this
- Failed validation triggered data clearing logic, removing valid data

## Solution Implemented
Fixed the SQL query in `validate_database_continuity()` to use correct column names:
- Changed `open, high, low, close` to `open_price, high_price, low_price, close_price`
- Maintained backward compatibility by mapping database columns to expected DataFrame column names

## Code Changes
- **okx_data_collector.py**: Updated `validate_database_continuity()` SQL query and column mapping

## Testing
- Syntax validation passed
- Column name mapping verified to match database schema
- Data validation should now work correctly without false failures

## Files Modified
- `scripts/okx_data_collector.py`: Fixed column names in database validation query

## Resolution Steps
1. Identified column name mismatch in validation query
2. Updated SQL query to use correct database column names
3. Ensured proper column mapping for DataFrame creation
4. Verified syntax and logic correctness