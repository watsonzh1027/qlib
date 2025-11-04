## Problem Description
After fixing the NameError for OKXDataCollector, a new ImportError occurred: `ModuleNotFoundError: No module named 'scripts'`. This was due to using an absolute import path that couldn't resolve from the `tests/` subdirectory.

## Solution
- Changed the import from `from scripts.okx_data_collector import OKXDataCollector` to `from ..scripts.okx_data_collector import OKXDataCollector` to use a relative import.

## Successful Steps Taken
1. Reviewed the error log to identify the import path issue.
2. Updated the import statement to use relative path syntax for accessing the parent directory's `scripts/` module.
3. Ran `conda activate qlib && pytest tests/test_collector.py --cov=scripts.okx_data_collector --cov-report=html --cov-report=term` to verify the import succeeds and tests begin collecting.
