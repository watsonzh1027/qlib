# Issue 0002: Fix test_fetch_data_rate_limit_retry TypeError

## Problem Description
The test `test_fetch_data_rate_limit_retry` in `tests/test_collect_okx.py` was failing with a `TypeError: object NoneType can't be used in 'await' expression` at line 41 in `qlib/scripts/data_collector/crypto/collector.py`.

## Root Cause
In the test, `mock_exchange.fetch_ohlcv.side_effect` was set to:
```python
[
    ccxt.RateLimitExceeded("Rate limit exceeded"),
    asyncio.Future().set_result(mock_ohlcv_data.values.tolist())
]
```

The issue was that `asyncio.Future().set_result(...)` returns `None`, so the second element in `side_effect` was `None`. When the retry logic called `await self.exchange.fetch_ohlcv(...)` the second time, it tried to await `None`, causing the TypeError.

## Solution
Create the `asyncio.Future` object separately, set its result, and then use the Future object in `side_effect`:
```python
future = asyncio.Future()
future.set_result(mock_ohlcv_data.values.tolist())
mock_exchange.fetch_ohlcv.side_effect = [
    ccxt.RateLimitExceeded("Rate limit exceeded"),
    future
]
```

## Steps Taken
1. Identified the issue by analyzing the test log and code.
2. Fixed the mock setup in `tests/test_collect_okx.py`.
3. Ran the test to confirm it passes.
4. Created this issue file to document the fix.

## Verification
The test now passes successfully, confirming the fix resolves the issue.

## Files Modified
- `tests/test_collect_okx.py`: Fixed the mock setup for `test_fetch_data_rate_limit_retry`.
