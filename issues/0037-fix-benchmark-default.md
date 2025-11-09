# Issue 0037: Fix benchmark defaulting to SH000300 when set to null

## Status: CLOSED
## Created: 2025-11-08 13:00:00

## Problem Description
When `benchmark` is set to `null` in the backtest configuration (as in crypto workflows), the system was incorrectly defaulting to the stock market benchmark "SH000300" instead of using no benchmark.

## Root Cause
In `qlib/backtest/report.py`, the `_cal_benchmark` method had flawed logic:
```python
benchmark = benchmark_config.get("benchmark", CSI300_BENCH)
```
When `benchmark_config` was an empty dict (created when benchmark=None), it would default to `CSI300_BENCH = "SH000300"`.

## Solution Implemented
Modified `_cal_benchmark` to properly check if benchmark is explicitly set to None:
```python
if benchmark_config is None or benchmark_config.get("benchmark") is None:
    return None
benchmark = benchmark_config.get("benchmark")
```

This ensures that when benchmark is None, no benchmark data is loaded, allowing crypto backtests to run without stock market benchmarks.

## Files Changed
- `qlib/backtest/report.py`: Fixed benchmark handling logic in `_cal_benchmark` method

## Testing
- Verified that crypto workflows can now run with `benchmark: null`
- Confirmed that existing stock workflows still work with proper benchmarks
- Backtest completes successfully without benchmark-related errors

## Resolution Time
Started: 2025-11-08 13:00:00
Completed: 2025-11-08 13:15:00