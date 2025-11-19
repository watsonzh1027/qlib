# Issue: Fix PostgreSQL table name mismatch in convert_to_qlib.py

## Status: CLOSED
## Created: 2025-11-18 21:08:00

## Problem Description
The script `convert_to_qlib.py` was failing with error: "Database query error: relation "kline_data" does not exist". The script was hardcoded to query table "kline_data", but the database setup script creates table "ohlcv_data". Additionally, the column names in the database are "open_price", "high_price", etc., but the script expected "open", "high", etc.

## Root Cause
- Table name mismatch: script used "kline_data", DB has "ohlcv_data"
- Column name mismatch: script schema used "open", DB has "open_price"
- Database schema not set up initially
- Partitioned table PRIMARY KEY issue in setup script

## Solution Steps
1. Updated `PostgreSQLStorage` initialization in `convert_to_qlib.py` to use table="ohlcv_data" and correct schema mapping:
   - 'open': 'open_price'
   - 'high': 'high_price'
   - 'low': 'low_price'
   - 'close': 'close_price'
   - 'volume': 'volume'

2. Added missing `ssl_mode` parameter to `PostgresConfig` dataclass.

3. Fixed database setup script `postgres_config.py`:
   - Changed DROP TABLE to drop "ohlcv_data" instead of "kline_data"
   - Modified table schema to use PRIMARY KEY (symbol, interval, timestamp) for partitioned table compatibility

4. Ran database schema setup with `setup_postgres_schema.py --drop-existing` to create the partitioned table structure.

## Final Result
Script now connects successfully to database. Finds 0 symbols (empty database) and exits cleanly. Data loading scripts can now populate the database for conversion to Qlib format.

## Files Modified
- `scripts/convert_to_qlib.py`: Updated table name and schema mapping
- `scripts/postgres_config.py`: Added ssl_mode, fixed drop table name, fixed PRIMARY KEY for partitioning