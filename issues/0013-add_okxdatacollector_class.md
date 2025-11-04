## Problem
Test collection failed with:
```
ImportError: cannot import name 'OkxDataCollector' from 'scripts.okx_data_collector'
```
The tests import `OkxDataCollector` but the module did not export that class.

## Solution (ONE ERROR)
- Implemented a minimal `OkxDataCollector` class in `scripts/okx_data_collector.py`.
- Behavior:
  - collect_data(symbol=None): calls `requests.get(...)` so mocked network exceptions propagate; returns `[]` for empty/unexpected JSON.
  - validate_data(data): raises `ValueError` for invalid formats and returns `True` for minimally valid dicts.

## Steps taken
1. Added `OkxDataCollector` class to the module with small, test-compatible behavior.
2. Kept implementation intentionally minimal to address just the import error.
3. Instructed to run tests and provide the new log for the next error fix (per ONE ERROR AT A TIME policy).

