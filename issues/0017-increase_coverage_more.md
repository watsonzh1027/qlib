## Problem
Coverage for `scripts/okx_data_collector.py` remained at ~70% and additional branches were not exercised by the existing tests.

## Solution
Added several targeted unit tests to `tests/test_collector.py` that exercise previously untested branches:
- save_klines behavior when no entries exist (returns False)
- save_klines writes and clears buffer (with os.makedirs and to_parquet patched)
- load_symbols reading a valid JSON config
- OkxDataCollector.validate_data success path
- OkxDataCollector.collect_data when resp.json() raises an exception (returns [])
- update_latest_data successful payload path and triggering save_klines
- main early exit when no symbols are loaded

## Steps taken
1. Appended focused tests to the primary test module `tests/test_collector.py` to keep test scope limited to the current module.
2. Used mocks for filesystem/network interactions to keep tests deterministic and fast.
3. Run the test suite targeting the module to confirm tests pass and coverage increases.

