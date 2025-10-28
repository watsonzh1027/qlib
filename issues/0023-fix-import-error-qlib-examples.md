# Issue 0023: Fix Import Error for qlib.examples Module

## Problem Description
The pytest command failed with `ModuleNotFoundError: No module named 'qlib.examples'` because the `predict_and_signal.py` file was located in the root `examples/` directory, but the test was trying to import it as `qlib.examples.predict_and_signal`.

## Root Cause
- The `examples/predict_and_signal.py` was at the project root level
- Test imports expected it under `qlib.examples`
- Import paths in the file were incorrect for the new location
- `load_model` function returns a tuple, but code expected a single object

## Solution
1. Moved `examples/predict_and_signal.py` to `qlib/examples/predict_and_signal.py`
2. Created `qlib/examples/__init__.py` to make it a proper Python package
3. Updated sys.path insertion to add the project root correctly
4. Fixed import statements to use relative paths from project root
5. Unpacked the tuple returned by `load_model` to get the model object
6. Fixed import in test file to use correct path

## Files Modified
- Moved: `examples/predict_and_signal.py` → `qlib/examples/predict_and_signal.py`
- Created: `qlib/examples/__init__.py`
- Modified: `qlib/examples/predict_and_signal.py` (sys.path, imports, load_model unpacking)
- Modified: `tests/test_predict_signal.py` (import path)

## Test Results
- Import error resolved
- 2 out of 3 tests now pass
- Remaining test failure in `test_main_cli` appears to be a separate issue with CLI argument handling

## Verification
Ran pytest command successfully without import errors:
```bash
pytest tests/test_predict_signal.py -v --cov=qlib.examples.predict_and_signal --cov=qlib.features.crypto_workflow.signal_rules --cov-report=term-missing --cov-report=html
