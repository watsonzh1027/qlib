# Issue 0007: Data Service Integration Fix

**Status:** CLOSED  
**Created:** 2026-01-22 01:55:00  
**Closed:** 2026-01-22 02:00:00

## Problem Description

After recent updates to `okx_data_collector.py`, the `data_service.py` script had compatibility issues that would cause failures when running automated data collection.

### Issues Found

1. **Command Line Argument Mismatch**
   - `data_service.py` was using `--start-time` and `--end-time` (with hyphens)
   - `okx_data_collector.py` expects `--start_time` and `--end_time` (with underscores)
   - This would cause command line parsing errors

2. **Time Format Mismatch**
   - `data_service.py` was formatting times as `%Y-%m-%d` (date only)
   - `okx_data_collector.py` expects ISO format: `%Y-%m-%dT%H:%M:%SZ`
   - This could lead to incorrect time ranges or parsing errors

## Root Cause

The `data_service.py` was not updated when `okx_data_collector.py` command line interface was standardized to use underscore-separated argument names and full ISO timestamp format.

## Solution

### Changes Made

#### File: `scripts/data_service.py`

**Change 1: Fixed OHLCV Collection Command Arguments**

Location: `DataService._collect_ohlcv_data()` method (around line 326)

```python
# Before:
cmd = [
    'python', 'scripts/okx_data_collector.py',
    '--output', 'db',
    '--start-time', start_time.strftime('%Y-%m-%d'),
    '--end-time', end_time.strftime('%Y-%m-%d')
]

# After:
cmd = [
    'python', 'scripts/okx_data_collector.py',
    '--output', 'db',
    '--start_time', start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
    '--end_time', end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
]
```

**Change 2: Fixed Funding Rate Collection Time Format**

Location: `DataService._collect_funding_rates()` method (around line 410)

```python
# Before:
success = collect_funding_rates_for_symbols(
    symbols=symbols,
    start_time=start_time.strftime('%Y-%m-%d'),
    end_time=end_time.strftime('%Y-%m-%d'),
    postgres_storage=postgres_storage
)

# After:
success = collect_funding_rates_for_symbols(
    symbols=symbols,
    start_time=start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
    end_time=end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
    postgres_storage=postgres_storage
)
```

### Testing

Created comprehensive test files:

1. **`tests/test_data_service_integration.py`**
   - Full unit tests with mocking
   - Tests command line argument format
   - Tests time format conversion
   - Tests funding rate conditional logic
   - Tests full update cycle workflow

2. **`tests/test_data_service_simple.py`**
   - Simple verification script
   - Can be run without mocking
   - Verifies key integration points

### Verification Steps

To verify the fix:

```bash
# Ensure qlib environment is activated
conda activate qlib

# Run simple verification
python tests/test_data_service_simple.py

# Or run full test suite
python tests/test_data_service_integration.py
```

Expected output:
```
✓ PASSED: Command Line Arguments
✓ PASSED: Function Signatures
✓ PASSED: DataServiceConfig
✓ PASSED: Time Format

Total: 4/4 tests passed
```

## Impact Assessment

### Before Fix
- `data_service.py start` would fail immediately with argument parsing errors
- Automated data collection would not work
- Manual intervention required for each data update

### After Fix
- `data_service.py start` works correctly
- Automated data collection runs successfully
- Proper time ranges are passed to data collector
- Funding rate collection works for future/swap markets

## Dependencies Verified

1. **Function Signatures** (all compatible):
   - `collect_funding_rates_for_symbols(symbols, start_time, end_time, postgres_storage)`
   - `load_symbols(path)`

2. **Command Line Arguments** (all compatible):
   - `--start_time` (underscore)
   - `--end_time` (underscore)
   - `--output` (choices: csv, db)
   - `--limit`
   - `--timeframes`

3. **Configuration Integration**:
   - `config/workflow.json` settings correctly read
   - PostgreSQL configuration properly passed
   - Market type conditional logic working

## Related Files

- `scripts/data_service.py` - Fixed
- `scripts/okx_data_collector.py` - Reference implementation
- `tests/test_data_service_integration.py` - Created
- `tests/test_data_service_simple.py` - Created

## Follow-up Actions

None required. Integration is fully working.

## Lessons Learned

1. **API Contract Consistency**: When updating command line interfaces, ensure all calling code is updated simultaneously
2. **Integration Testing**: Always test integration points between modules after interface changes
3. **Time Format Standards**: Use ISO 8601 format consistently across the codebase
4. **Documentation**: Keep function signatures and command line arguments documented

## Notes

- The fix maintains backward compatibility with existing workflows
- No database schema changes required
- No configuration file changes required
- Users running automated data service will see immediate improvement
