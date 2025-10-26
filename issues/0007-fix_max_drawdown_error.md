# Issue 0007: Fix TypeError in _calculate_max_drawdown method

## Problem Description
The `_calculate_max_drawdown` method in `qlib/backtest/crypto.py` was failing with a `TypeError: float() argument must be a string or a real number, not '_NoValueType'` when calling `drawdown.min()` on pandas Series containing pandas NA values (pd.NA).

## Root Cause
- The drawdown calculation `(equity - peak) / peak` could result in pd.NA values when equity or peak contain invalid values.
- Calling `drawdown.min()` on a Series with pd.NA values causes the underlying numpy array to contain '_NoValueType', which cannot be converted to float.
- The existing checks (`drawdown.empty` or `drawdown.isna().all()`) did not prevent this issue.

## Solution
1. **Modified `_calculate_max_drawdown` method**:
   - Use `drawdown.dropna()` to remove NA values before finding the minimum.
   - Use `np.nanmin(drawdown_clean.values)` to safely compute the minimum, handling any remaining NaN/inf values.
   - Check for finite values before returning.

2. **Updated test assertions**:
   - Modified `test_risk_metrics` to use `np.nanmin()` on cleaned drawdown values for comparison.
   - Modified `test_position_limits` to use `np.nanmax()` on cleaned position values to avoid similar issues.

## Files Changed
- `qlib/backtest/crypto.py`: Updated `_calculate_max_drawdown` method to handle pd.NA values properly.
- `tests/test_backtest.py`: Updated test assertions to use numpy functions for safe min/max calculations.

## Testing
- All 6 tests in `tests/test_backtest.py` now pass.
- Coverage for `qlib/backtest/crypto.py` is 96%.

## Verification
- Ran `pytest tests/test_backtest.py --cov=qlib.backtest.crypto` successfully.
- No more TypeError exceptions related to '_NoValueType'.
- Drawdown calculations now handle edge cases with invalid data gracefully.
