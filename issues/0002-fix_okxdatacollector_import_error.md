## Problem Description
After adding new tests to improve coverage, 4 tests failed with `NameError: name 'OKXDataCollector' is not defined`. This occurred because the class was not imported in `tests/test_collector.py`, despite existing tests passing (likely due to prior imports).

## Solution
- Added `from scripts.okx_data_collector import OKXDataCollector` at the top of `tests/test_collector.py`.
- This fixed the import issue for all new test functions.

## Successful Steps Taken
1. Reviewed the test failure log to confirm the error was a missing import.
2. Located the import section in the test file and added the necessary import statement.
3. Ran `conda activate qlib && pytest tests/test_collector.py --cov=scripts.okx_data_collector --cov-report=html --cov-report=term` to verify all tests now pass and coverage remains at 75% (awaiting further improvements).
