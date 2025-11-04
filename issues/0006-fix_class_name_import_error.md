## Problem Description
The import `from scripts.okx_data_collector import OKXDataCollector` failed with `ImportError: cannot import name 'OKXDataCollector'`. The error suggested the name might be 'okx_data_collector', indicating a mismatch in class naming (likely `OkxDataCollector` in camelCase).

## Solution
- Updated the import to `from scripts.okx_data_collector import OkxDataCollector`.
- Adjusted all new test functions to instantiate `OkxDataCollector()` instead of `OKXDataCollector()`.

## Successful Steps Taken
1. Reviewed the error log to identify the incorrect class name.
2. Inspected the module naming convention and updated to `OkxDataCollector`.
3. Modified the test file accordingly.
4. Ran `conda activate qlib && pytest tests/test_collector.py --cov=scripts.okx_data_collector --cov-report=html --cov-report=term` to verify the import and tests work.
