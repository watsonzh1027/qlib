## Problem
Tests failed with:
```
NameError: name 'handle_funding_rate' is not defined
```
Root cause: the test file called `handle_funding_rate(...)` directly but did not import that symbol into the test namespace.

## Solution (ONE ERROR)
- Imported `handle_funding_rate` into `tests/test_collector.py`:
  - `from scripts.okx_data_collector import handle_ohlcv, handle_funding_rate`

## Steps taken
1. Added a minimal import line in the test file to expose `handle_funding_rate` to tests.
2. This change targets only the single failing NameError so pytest can proceed to the next error.

## Next step
- Run tests and provide the new log. I will address the next failing error only after you confirm.
