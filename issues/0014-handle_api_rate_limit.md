## Problem
Test `test_handle_api_rate_limit` expected `collect_data()` to raise when the HTTP response status was 429. Previously `collect_data` ignored HTTP status and returned [].

## Solution (ONE ERROR)
- Updated `OkxDataCollector.collect_data` to raise an Exception when `resp.status_code` is >= 400 (covers 429).

## Steps taken
1. Added an HTTP status check inside `collect_data` and raise on error codes.
2. Kept remaining behavior unchanged so other tests continue to behave as before.

## Next step
- Run tests and share the new test output so the next failing issue can be addressed (ONE ERROR AT A TIME).
