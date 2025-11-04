## Problem
Tests failed during collection/runtime with:
```
NameError: name 'handle_ohlcv' is not defined
```
Root cause: the test file imported the module object (e.g. `import scripts.okx_data_collector as collector`) but called `handle_ohlcv(...)` directly; the symbol was not present in the test namespace.

## Solution (ONE ERROR)
- Added `from scripts.okx_data_collector import handle_ohlcv` to the test file to import the symbol into the test namespace.
- This is a minimal, single-error fix to allow pytest to proceed to the next failing assertion/error.

## Steps taken
1. Inspected the test log to identify the first failing NameError.
2. Updated `tests/test_collector.py` to import `handle_ohlcv` directly.
3. Instructed to run tests and provide the updated log for the next iteration.

