# Issue 0010: Fix Import Error for setup_project_structure in Test

## Problem Description
The test `tests/test_setup_dirs.py` failed with ImportError: `ModuleNotFoundError: No module named 'qlib.scripts.setup_project_structure'`.

## Root Cause
- The import statement was `from qlib.scripts.setup_project_structure import setup_project_directories`
- However, the file `setup_project_structure.py` is located in the root `scripts/` directory, not in `qlib/scripts/`
- The `scripts/` directory is not part of the `qlib` package, so the import path was incorrect

## Solution Applied
1. Modified the import in `tests/test_setup_dirs.py` to `from scripts.setup_project_structure import setup_project_directories`
2. Added `sys.path` manipulation to include the project root in the Python path:
   ```python
   import sys
   sys.path.insert(0, str(Path(__file__).parent.parent))
   ```
3. Fixed the test logic by removing incorrect `pytest.MonkeyPatch` usage and directly passing the test directory to `setup_project_directories(test_dir)`

## Verification
- Re-ran the pytest command: `pytest tests/test_setup_dirs.py -v`
- Test now passes: `tests/test_setup_dirs.py::test_directory_creation PASSED`

## Files Modified
- `tests/test_setup_dirs.py`: Updated import and test logic

## Notes
- The `setup_project_structure.py` file remains in the `scripts/` directory as per user preference
- The test now correctly imports and uses the function for directory creation testing
