## Problem
Current coverage for `scripts/okx_data_collector.py` is ~77%. Additional branches (main shutdown path, update error handling, collect_data missing payload, funding rate handler) are not exercised.

## Solution
Added focused unit tests to `tests/test_collector.py` that:
- Verify OkxDataCollector.collect_data returns [] when JSON lacks 'data'.
- Confirm update_latest_data handles HTTP errors from resp.raise_for_status without crashing.
- Exercise handle_funding_rate to ensure values are normalized and stored.
- Run the main() flow with a fake exchange and simulate KeyboardInterrupt to exercise finally block, ensuring save_klines and exchange.close are executed.

## Steps taken
1. Implemented tests that mock network, exchange, and filesystem interactions where appropriate.
2. Kept tests limited to the primary test module to avoid broader test collection.
3. Instructed to run pytest for the single module to measure coverage improvement.

## Expected result
Running:
- conda activate qlib
- pytest tests/test_collector.py --cov=scripts.okx_data_collector --cov-report=html --cov-report=term

Should increase coverage significantly; if target (95%) is not reached, provide the updated coverage report and I will add further focused tests (ONE ERROR / ONE GAP at a time).
