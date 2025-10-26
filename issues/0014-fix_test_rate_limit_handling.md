# Issue 0014: Fix test_rate_limit_handling in test_collector_skeleton.py

## Problem Description
The test `test_rate_limit_handling` was failing with `AssertionError: assert 0 == 2` on `len(mock_exchange.fetch_ohlcv.mock_calls)`. This occurred because the `CryptoCollector` instance was created before the `patch` context manager, causing `self.exchange` to be set to the real `ccxt.okx` instance instead of the mocked one. Additionally, the code was using synchronous `ccxt`, which didn't align with the async test setup.

## Root Cause
- Collector instantiation outside the patch block meant mocking didn't apply to the exchange instance.
- Use of sync `ccxt` in an async context.
- Mock was not set up as an async mock, causing `TypeError: object list can't be used in 'await' expression`.

## Solution
1. Updated `examples/collect_okx_ohlcv.py` to use `ccxt.async_support` and await the `fetch_ohlcv` call.
2. Moved `CryptoCollector` instantiation inside the `with patch` block in the test.
3. Updated the patch target to `'ccxt.async_support.okx'`.
4. Used `AsyncMock` for the `fetch_ohlcv` method to handle async calls.
5. Changed assertion to check `call_args_list` instead of `mock_calls` for async mocks.
6. Removed duplicate assertion.

## Changes Made
- Modified import in `examples/collect_okx_ohlcv.py` to `import ccxt.async_support as ccxt`.
- Added `await` to `self.exchange.fetch_ohlcv` in `_fetch_ohlcv`.
- Repositioned collector creation in `tests/test_collector_skeleton.py`.
- Adjusted patch path and used `AsyncMock`.
- Updated assertion to use `call_args_list`.

## Testing
Ran `pytest tests/test_collector_skeleton.py::test_rate_limit_handling -v` and confirmed the test now passes.

## Files Affected
- `examples/collect_okx_ohlcv.py`
- `tests/test_collector_skeleton.py`
