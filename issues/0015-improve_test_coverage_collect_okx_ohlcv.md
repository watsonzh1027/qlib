# Issue 0015: Improve Test Coverage for collect_okx_ohlcv.py

## Problem Description
The test coverage for `examples/collect_okx_ohlcv.py` was at 92% with missing lines 29 and 37. After adding additional tests, coverage improved to 98% with only one branch partial coverage remaining (29->exit).

## Root Cause
- Line 29: The `pass` statement in `main()` was not executed.
- Line 37: The code after `main()` was not reached.
- Branch coverage: The exit branch in the retry loop was not fully covered.

## Solution Implemented
Added three new test cases to `tests/test_collector_skeleton.py`:

1. `test_fetch_data_max_retries_exceeded()`: Tests the scenario where rate limit retries are exhausted, covering the full retry loop and exception raising.
2. `test_fetch_data_other_exception()`: Tests handling of non-rate-limit exceptions, ensuring error logging is covered.
3. `test_main()`: Tests the `main()` function to cover the previously uncovered `pass` statement.

## Changes Made
- Added `test_fetch_data_max_retries_exceeded` to test max retry exhaustion.
- Added `test_fetch_data_other_exception` to test other exception handling.
- Added `test_main` to cover the main function.

## Testing Results
- All 8 tests pass.
- Coverage improved from 92% to 98%.
- Only one branch partial coverage remains (29->exit), which is the exit condition in the retry loop.

## Files Modified
- `tests/test_collector_skeleton.py`: Added three new test functions.

## Verification
Run the following command to verify:
```bash
conda activate qlib && pytest tests/test_collector_skeleton.py --cov=examples.collect_okx_ohlcv --cov-report=term-missing
```

Expected output: 8 passed, coverage 98%.
