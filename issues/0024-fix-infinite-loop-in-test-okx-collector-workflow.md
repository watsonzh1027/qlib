# Issue 0024: Fix Infinite Loop in test_okx_collector_workflow

## Problem Description
The `test_okx_collector_workflow` function in `tests/test_collect_okx.py` was entering an infinite loop during execution. The test log showed repeated iterations with the same `current_time` value, indicating that the loop condition in the `collect_historical` method of `OKXCollector` was never satisfied.

## Root Cause
The mock setup for `fetch_ohlcv` was configured to always return the same data on every call. In the `collect_historical` method, the loop updates `current_time` to `batch[-1][0] + 1` after each batch. Since the mock always returned the same data, `current_time` was set to the same value repeatedly, preventing it from ever reaching `end_ts`.

## Solution
Modified the mock to use `side_effect` with a list of `asyncio.Future` objects:
- First call returns the mock OHLCV data
- Subsequent calls return an empty list to break the loop

Additionally, simplified the test assertions to focus on verifying the output file and data content, removing dependencies on undefined fixtures like `test_data_dir`.

## Files Modified
- `tests/test_collect_okx.py`: Updated the mock setup and test assertions in `test_okx_collector_workflow`

## Verification
The test now passes successfully without entering an infinite loop, and the collected data is correctly saved to the output parquet file.
