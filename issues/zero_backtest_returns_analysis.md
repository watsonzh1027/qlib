# Fix Summary: Zero Backtest Returns - Funding Rate Features Not Generated

## Date: 2026-01-13

## Problem
After fixing the `CryptoAlpha158WithFunding` import issue, the workflow ran successfully but produced zero returns:
- All metrics (mean, std, annualized_return, max_drawdown) = 0.0
- information_ratio = NaN
- Model predictions were essentially constant (~0.000393)

## Root Cause Analysis

### 1. **Critical Bug: Wrong Method Name**
The `CryptoAlpha158WithFunding` class defined `fetch_data()` instead of `fetch()`:
- Base class `DataHandlerLP` uses `fetch()` method
- Handler defined `fetch_data()` which was never called
- Result: Funding rate features were never added to the dataset

### 2. **MultiIndex Access Error**
When trying to access instrument-specific data, the code used:
```python
inst_dates = df_alpha.loc[inst].index  # Wrong!
```

This fails with MultiIndex DataFrames. Should use:
```python
inst_dates = df_alpha.xs(inst, level='instrument').index  # Correct!
```

### 3. **Missing Funding Rate Data**
Only BTC and ETH have funding rate CSV files in `data/funding_rates/`:
- ✅ BTC_USDT_USDT_funding_rate.csv
- ✅ ETH_USDT_USDT_funding_rate.csv
- ❌ XRP_USDT_USDT_funding_rate.csv (missing)
- ❌ AAVE, BNB, SOL (missing)

## Fixes Applied

### Fix 1: Rename `fetch_data()` to `fetch()`
**File**: `/home/watson/work/qlib/qlib/contrib/data/handler_crypto.py`

```python
# Before
def fetch_data(self):
    df_alpha = super().fetch_data()
    
# After  
def fetch(self):
    df_alpha = super().fetch()
```

### Fix 2: Fix MultiIndex Access
**File**: `/home/watson/work/qlib/qlib/contrib/data/handler_crypto.py`

```python
# Before (lines 193, 208)
inst_dates = df_alpha.loc[inst].index

# After
inst_dates = df_alpha.xs(inst, level='instrument').index
```

## Verification

After fixes, the handler now correctly generates funding rate features:

```
2026-01-13 20:35:46 | INFO | Loaded 100 funding rate records for BTC_USDT_4H_FUTURE
2026-01-13 20:35:46 | INFO | Loaded 100 funding rate records for ETH_USDT_4H_FUTURE
2026-01-13 20:35:46 | WARNING | Funding rate file not found: data/funding_rates/XRP_USDT_USDT_funding_rate.csv
2026-01-13 20:35:46 | WARNING | No funding rate data for XRP_USDT_4H_FUTURE, filling with zeros
2026-01-13 20:35:46 | INFO | Combined features shape: (13146, 168)
```

**Feature count increased from 159 to 168** (9 new funding rate features added):
- funding_rate
- funding_rate_ma7
- funding_rate_ma30
- funding_rate_std7
- funding_rate_std30
- funding_rate_extreme
- funding_rate_zscore
- funding_rate_momentum
- funding_rate_cumsum

## Next Steps

1. ✅ Fixed method name and MultiIndex access
2. ⚠️ Re-run workflow to verify model learns better patterns with funding rate features
3. ⚠️ Consider fetching funding rate data for XRP, AAVE, BNB, SOL
4. ⚠️ Update backtest end_time to 2025-12-31 (currently 2026-01-07, beyond test set)
5. ⚠️ Monitor if model predictions have better variance with funding rate features

## Expected Outcome

With funding rate features now properly included:
- Model should learn more meaningful patterns
- Predictions should have higher variance
- Backtest should generate actual trading signals
- Returns should no longer be zero

## Files Modified

1. `/home/watson/work/qlib/qlib/contrib/data/handler_crypto.py`
   - Line 162: `fetch_data()` → `fetch()`
   - Line 170: `super().fetch_data()` → `super().fetch()`
   - Line 193: `df_alpha.loc[inst]` → `df_alpha.xs(inst, level='instrument')`
   - Line 208: `df_alpha.loc[inst]` → `df_alpha.xs(inst, level='instrument')`
