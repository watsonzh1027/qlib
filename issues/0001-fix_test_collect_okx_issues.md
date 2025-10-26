# Issue 0001: Fix test_collect_okx.py Test Failures

## Problem Description
All test cases in `test_collect_okx.py` failed due to the following errors:
1. **`FileNotFoundError`**: The config file `config_defaults.yaml` was not found at the expected path.
2. **`NameError`**: The `ccxt` module was not imported in `test_collect_okx.py`.
3. **`TypeError`**: The `CryptoCollector.__init__()` method does not support the `config` parameter.

## Solution
1. **Fixed `FileNotFoundError`**:
   - Updated the path in `_load_config` to point to the correct location of `config_defaults.yaml`.
2. **Fixed `NameError`**:
   - Added `import ccxt` to `test_collect_okx.py`.
3. **Fixed `TypeError`**:
   - Removed the `config` parameter from `test_full_collection_workflow`.

## Verification
Run the following command to verify the fixes:
```bash
pytest tests/test_collect_okx.py -v
```

## Notes
- Ensure the `qlib` environment is activated before running tests.
- The config file must exist at `/home/watson/work/qlib/features/crypto-workflow/config_defaults.yaml`.