## Problem
A unit test failed with:
```
AssertionError: assert 'BTC/USDT' in {}
```
The test called `handle_funding_rate(...)` but the module-level `funding_rates` dict remained empty.

## Solution (ONE ERROR)
- Added `global funding_rates` inside `handle_funding_rate` to ensure the function mutates the module-level dictionary.
- Normalized symbol to `"BASE/QUOTE"` form using `symbol.replace('-', '/')` and removed spaces.
- Returned True to make the handler's effect explicit for tests (minimal change).

## Steps taken
1. Inspected failing test log to identify the first failing assertion.
2. Modified `scripts/okx_data_collector.py` to explicitly write to the module-level `funding_rates` dict.
3. Kept changes minimal (ONE ERROR) so further failures can be handled in separate iterations.

## Verification
- Run:
  - conda activate qlib
  - pytest tests/test_collector.py --cov=scripts.okx_data_collector --cov-report=html --cov-report=term
- Provide the new test log and I will address the next failing test per the ONE ERROR AT A TIME rule.
