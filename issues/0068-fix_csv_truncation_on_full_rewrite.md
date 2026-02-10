Status: OPEN
Created: 2026-02-08 00:00:00

# Problem Description
User reported that ETHUSDT_1m.csv previously contained full history, but after running the collector, data after 2022-11-27 was missing. This indicates a truncation during CSV write when the collector fell back to the full rewrite path instead of appending or merging.

# Final Solution
- Add a regression test to ensure the full rewrite path merges existing CSV data instead of truncating.
- Update `save_klines` to merge existing CSV data with new data before a full rewrite.

# Update Log
- Added regression test `test_save_klines_full_rewrite_merges_existing_data` in tests/test_okx_data_collector.py.
- Updated save_klines full rewrite path to merge existing CSV data before writing.
- Ran pytest tests/test_okx_data_collector.py -k full_rewrite_merges_existing_data (passed, 1 warning from SQLAlchemy deprecation).
