# Issue: Crypto Collector Not Respecting workflow.json and Missing Files

## Description
The `CryptoCollector` was not correctly loading settings from `config/workflow.json` and failed to save files due to invalid symbol characters in filenames.

## Root Causes
1. **Config Loading**: The `Run` class was looking for `data_dir` at the top level, but `workflow.json` has it under `data.csv_data_dir`.
2. **Symbol Resolution**: The `symbols` file path was not being resolved correctly relative to the project root, and the `symbol_file` argument was ignored if not provided via CLI.
3. **Symbol Normalization**: Loaded symbols were not normalized to include `/` (e.g., `BTCUSDT` vs `BTC/USDT`), causing CCXT errors.
4. **Filename Issues**: Symbols with `/` caused `OSError` because pandas tried to save to subdirectories that didn't exist.
5. **Timezone/Localization**: Date comparison in `get_data_from_remote` failed due to mixing localized and naive timestamps.

## Changes
- Updated `Run.__init__` to correctly parse the nested structure of `workflow.json`.
- Updated `Run.download_data` to load `symbol_file` and resolve its path correctly.
- Added automatic normalization to `get_cg_crypto_symbols`.
- Fixed `CryptoCollector.normalize_symbol` to replace `/` with `_` for safe filenames.
- Ensured consistent UTC localization for date filtering in `get_data_from_remote`.
- Added a dedicated log file `logs/crypto_collector.log` for better observability.

## Verification Results
- Verified that `Run` now correctly loads 6 symbols from `config/top50_symbols.json` as specified in `workflow.json`.
- Verified file creation: `data/klines/AAVE_USDT.csv` was successfully created with hourly data.
- Verified that `limit_nums` correctly restricts the number of processed symbols.

## Status
CLOSED
