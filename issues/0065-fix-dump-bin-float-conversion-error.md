# Fix dump_bin.py Float Conversion Error

## Symptom
Running `python scripts/dump_bin.py dump_all` fails with:
`ValueError: could not convert string to float: '2019-12-31 16:00:00'`

## Root Cause
The `_data_to_bin` method in `scripts/dump_bin.py` attempts to convert all columns (except excluded ones and symbol/date columns) to float32. The input CSV contains a `datetime` column (string representation of date) which was not excluded and not numeric, causing the conversion to fail.

## Solution
Modified `scripts/dump_bin.py` to check if a column is numeric (`np.issubdtype(dtype, np.number)`) before attempting to dump it as a feature. Non-numeric columns are now skipped.

## Verification
Created a reproduction test `tests/test_dump_bin_repro.py` which creates a dummy CSV with a string column and runs the dump process. The test passes, confirming the fix prevents the crash and correctly skips the string column.

## Status
CLOSED
