# Issue 0044: Fix current_since increment in data collection loop

## Status: CLOSED
## Created: 2025-11-15 12:00:00

## Problem Description
In the `update_latest_data` function's data collection loop, when receiving empty responses from the OKX API, the `current_since` timestamp was being incremented by a hardcoded value of 60000 milliseconds (1 minute). This caused issues when using different timeframes other than 1m.

Additionally, the increment logic didn't properly account for advancing to the next timeframe slot after an empty response.

## Root Cause
- Hardcoded increment of 60000ms assumed 1m timeframe
- No dynamic calculation based on actual TIMEFRAME configuration
- Empty responses should advance by the full timeframe duration to skip empty slots

## Solution Implemented
1. Added `timeframe_to_ms()` function to dynamically convert timeframe strings ('1m', '5m', '1h', '1d') to milliseconds
2. Replaced hardcoded `current_since += 60000` with `current_since += timeframe_to_ms(TIMEFRAME)`

## Code Changes
- Added `timeframe_to_ms()` function in `scripts/okx_data_collector.py`
- Modified the empty response handling in `update_latest_data()` to use dynamic timeframe calculation

## Testing
- Verified function returns correct millisecond values for different timeframes
- Syntax check passed
- For 1m timeframe, behavior remains identical (60000ms increment)
- For other timeframes, now advances by correct duration

## Files Modified
- `scripts/okx_data_collector.py`: Added timeframe_to_ms function and updated increment logic

## Resolution Steps
1. Identified the hardcoded increment issue
2. Implemented dynamic timeframe calculation
3. Tested the changes
4. Verified backward compatibility for 1m timeframe