## Problem Description
The relative import `from ..scripts.okx_data_collector import OKXDataCollector` failed with `ImportError: attempted relative import beyond top-level package`. This happened because pytest couldn't resolve the parent package from the project root.

## Solution
- Added `import sys; sys.path.insert(0, '..')` to include the project root in the Python path.
- Reverted the import to absolute: `from scripts.okx_data_collector import OKXDataCollector`.

## Successful Steps Taken
1. Reviewed the error log to identify the path resolution issue.
2. Modified the test file to adjust `sys.path` and use absolute import.
3. Ran `conda activate qlib && pytest tests/test_collector.py --cov=scripts.okx_data_collector --cov-report=html --cov-report=term` to verify the import succeeds and tests begin collecting.
