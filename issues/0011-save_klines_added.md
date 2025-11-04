## Problem
Tests failed with:
```
NameError: name 'save_klines' is not defined
```
The test `test_save_klines` calls `save_klines('BTC/USDT')` but the function did not exist.

## Solution (ONE ERROR)
- Added a minimal `save_klines(symbol, base_dir='data/klines')` implementation in `scripts/okx_data_collector.py`.
- Behavior:
  - Reads from module-level `klines` dict.
  - Converts entries to `pandas.DataFrame`.
  - Ensures output directory exists (`os.makedirs`).
  - Calls `DataFrame.to_parquet(filepath, index=False)` (tests mock this).
  - Clears the symbol buffer and returns True when saved, False if no data.

## Steps taken
1. Implemented `save_klines` in the module with the minimal behavior required by tests.
2. Kept calls to `os.makedirs` and `DataFrame.to_parquet` so tests can patch them.
3. Ran tests locally to proceed to next failing error (please run tests and provide the new log for the next iteration).

