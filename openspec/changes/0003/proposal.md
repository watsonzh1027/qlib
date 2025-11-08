# Change Proposal: 0003-modify-convert-to-qlib

## Summary
Modify the `convert_to_qlib` module to correctly convert CSV data from the `klines` directory to Qlib-compatible binary format, following the principles of `dump_bin.py`. The output should be saved to the `qlib_data/crypto` directory as specified in `workflow.json`.

## Motivation
The current `convert_to_qlib.py` incorrectly converts data to Parquet format instead of the required binary format for Qlib. This change ensures proper data conversion for quantitative research and backtesting.

## Impact
- Fixes data conversion pipeline for crypto OHLCV data.
- Aligns with Qlib's binary data requirements.
- Uses configuration from `workflow.json` for directory paths.

## Related Changes
- Depends on existing `dump_bin.py` logic.
- Updates data flow in the project.

## Status
Proposed