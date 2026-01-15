# Issue 0064: Resolved Qlib Data Loading and Funding Rate Integration

## Problem Description
Qlib was failing to load data for the `CryptoAlpha158WithFunding` data handler. Additionally, the `collector.py` CLI was broken due to method renaming and hierarchical symbol flattening.

## Solution
1. **Lowercase Feature Paths**: Modified `convert_to_qlib.py` to ensure feature directories and `.bin` files are lowercased, matching Qlib internal expectations.
2. **Hierarchical Symbol Handling**: Updated `symbol_utils.py` and `collector.py` to correctly handle `BASE_QUOTE/interval/market` symbols without flattening them during download or path generation.
3. **CLI Restoration**: Renamed methods in `Run` class back to `download` and `normalize` for `fire` CLI compatibility. Added `limit` and `market_type` as global flags.
4. **CCXT Symbol Extraction**: Fixed `get_ccxt_symbol` to accurately extract the base symbol from hierarchical Qlib symbols for exchange API calls.
5. **Comprehensive Testing**: 
    - Verified `test_loading.py` returns (4469, 534) data.
    - Achieved 92% coverage for `handler_crypto.py`.
    - Achieved 90% coverage for `collector.py` with 19 passing tests.

## Verification Results
- `python scripts/data_collector/crypto/collector.py download -i 1h`: SUCCESS (Verified clean paths like `AAVE_USDT/1h/future/AAVE_USDT.csv`).
- `pytest tests/test_crypto_handler.py`: PASSED (92% coverage).
- `pytest tests/test_crypto_collector.py`: PASSED (90% coverage).

## Status
**CLOSED**
