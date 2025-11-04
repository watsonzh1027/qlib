## Problem
Tests failed with:
```
NameError: name 'save_klines' is not defined
```
The test calls `save_klines(...)` directly but the symbol was not imported into the test module.

## Solution (ONE ERROR)
- Added `from scripts.okx_data_collector import save_klines` to `tests/test_collector.py` (alongside other direct imports).
- This is a minimal, single-error fix so pytest can proceed to the next failing assertion/error.

## Steps taken
1. Updated `tests/test_collector.py` to import `save_klines`.
2. Instructed to run tests and provide the updated log for the next iteration.

