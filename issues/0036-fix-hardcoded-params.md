# Issue 0036: Fix hardcoded parameters in convert_to_qlib.py

## Status: CLOSED
## Created: 2025-11-08 12:00:00

## Problem Description
The `convert_to_qlib.py` script had several hardcoded parameters that should be configurable via `workflow.json`:
- `interval`/`freq` was hardcoded as "15T" in `validate_data_integrity` and extracted from data instead of config
- Parameters like `date_field_name`, `symbol_field_name`, `exclude_fields` were hardcoded
- The script did not use the `data_convertor` section from `workflow.json`

## Root Cause
The code was not following the centralized configuration approach, making it inflexible for different data formats and intervals.

## Solution Implemented
1. **Modified `validate_data_integrity` function**: Added `freq` parameter to accept dynamic frequency instead of hardcoded "15T".

2. **Updated `convert_to_qlib` function**:
   - Retrieve `interval` from `data_collection.interval` in `workflow.json`
   - Convert interval to qlib frequency using `config_manager._convert_ccxt_freq_to_qlib()`
   - Use `data_convertor.date_field_name` for date field
   - Use `data_convertor.include_fields` to determine which fields to include
   - Dynamically set `exclude_fields` based on date, symbol, and interval columns

3. **Updated dumper initialization**: Pass the retrieved parameters to `DumpDataCrypto` instead of hardcoded values.

## Files Changed
- `scripts/convert_to_qlib.py`: Modified parameter handling and function signatures

## Testing
- Verified that the script now reads parameters from `workflow.json`
- Ensured backward compatibility with existing data structure
- Tested with sample data to confirm conversion works with configurable parameters

## Resolution Time
Started: 2025-11-08 12:00:00
Completed: 2025-11-08 12:30:00