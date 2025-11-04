## Problem
Overall coverage for `scripts/okx_data_collector.py` was low (~70%). Some branches were not exercised (e.g., save_klines empty/no-data path, buffer clearing after save, load_symbols valid-file, OkxDataCollector.validate_data success, collect_data successful payload path, update_latest_data triggering save).

## Solution
Added targeted unit tests to increase coverage:

- tests/test_collector_extra.py:
  - test_save_klines_no_entries_returns_false
  - test_save_klines_clears_buffer
  - test_load_symbols_valid_json
  - test_okxdatacollector_validate_success
  - test_collect_data_returns_payload_on_success
  - test_update_latest_data_triggers_save

These tests use mocks for filesystem and network interactions where appropriate, keeping tests fast and deterministic.

## Steps taken
1. Created tests that exercise previously untested branches.
2. Used existing project conventions for imports (sys.path insertion).
3. Kept tests minimal and robust to avoid brittleness.
4. Run test suite and confirmed tests pass; coverage should increase. If additional uncovered lines remain, provide the updated coverage log and I will address the next gap (ONE ERROR AT A TIME).
