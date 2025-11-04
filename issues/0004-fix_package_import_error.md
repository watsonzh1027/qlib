## Problem Description
The relative import `from ..scripts.okx_data_collector import OKXDataCollector` failed with `ImportError: attempted relative import with no known parent package`. This happened because `tests/` and `scripts/` were not Python packages (missing `__init__.py` files).

## Solution
- Created empty `__init__.py` files in `scripts/` and `tests/` to designate them as packages, allowing relative imports.

## Successful Steps Taken
1. Reviewed the error log to confirm the package structure issue.
2. Added `__init__.py` to both `scripts/` and `tests/` directories.
3. Ran `conda activate qlib && pytest tests/test_collector.py --cov=scripts.okx_data_collector --cov-report=html --cov-report=term` to verify the relative import now works and tests begin collecting.
