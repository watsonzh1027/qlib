## Problem Description
Test coverage for `scripts/okx_data_collector.py` was at 75% (22 missed statements out of 89). This indicated gaps in testing error handling, edge cases, and data validation paths.

## Solution
- Added 4 new test functions in `tests/test_collector.py` to cover network errors, empty responses, invalid data formats, and rate limiting.
- Tests were written following TDD: defined expected behavior first, then ensured they exercise previously uncovered code.
- Ran `conda activate qlib && pytest tests/test_collector.py --cov=scripts.okx_data_collector --cov-report=html --cov-report=term` to verify improvements.
- Coverage increased to approximately 90% after implementation.

## Successful Steps Taken
1. Reviewed HTML coverage report to pinpoint missed lines (e.g., exception branches in API calls).
2. Added targeted unit tests using mocks for external dependencies.
3. Iterated on tests one at a time, ensuring each new test covered at least one missed statement.
4. Confirmed all tests pass and coverage improved without introducing regressions.
