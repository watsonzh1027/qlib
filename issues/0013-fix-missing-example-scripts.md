# Issue 0013: Fix Missing Example Scripts

## Problem Description
The test `tests/test_examples_stubs.py` was failing because several example scripts were missing from the `examples/` directory:
- `preprocess_features.py`
- `train_lgb.py`
- `predict_and_signal.py`
- `backtest.py`

These scripts are referenced in the `EXAMPLE_SCRIPTS` list in the test file and are expected to exist for the crypto workflow.

## Root Cause
The example scripts were not created as part of the project setup, causing the test to fail with `FileNotFoundError` for the missing files.

## Solution
Created stub implementations for all missing example scripts with proper `__main__` guards:

1. `examples/preprocess_features.py` - Stub for feature preprocessing
2. `examples/train_lgb.py` - Stub for LightGBM model training
3. `examples/predict_and_signal.py` - Stub for prediction and signal generation
4. `examples/backtest.py` - Stub for backtesting

Each script includes:
- A shebang line (`#!/usr/bin/env python3`)
- A docstring describing the script's purpose
- A `main()` function with placeholder implementation
- Proper `if __name__ == "__main__":` guard

## Testing
- Ran `pytest tests/test_examples_stubs.py -v` successfully
- All 11 tests now pass, including:
  - `test_example_scripts_exist` - Verifies all scripts exist
  - `test_script_imports` - Verifies scripts can be imported
  - `test_script_main_guard` - Verifies proper main guards

## Files Changed
- `examples/preprocess_features.py` (created)
- `examples/train_lgb.py` (created)
- `examples/predict_and_signal.py` (created)
- `examples/backtest.py` (created)

## Verification
- All tests in `tests/test_examples_stubs.py` now pass
- Scripts are executable and have proper structure for future implementation
