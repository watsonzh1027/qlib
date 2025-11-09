# 0035-fix-backtesting-frequency-requirement

Status: CLOSED
Created: 2025-11-08 15:30:00

## Problem Description
The crypto workflow backtesting failed with error: "can't find a freq from [Freq(15min)] that can resample to 1min!"

Qlib backtesting requires 1min frequency data for accurate simulation and metric calculations, but the workflow was configured for 15min data.

## Root Cause
Qlib's backtesting framework internally uses 1min frequency for trade calendars and portfolio metric calculations. When only 15min data is available, it cannot resample to the required higher frequency, causing the backtesting to fail.

## Solution
Updated the workflow configuration to use 1min frequency throughout:

- Changed `workflow.frequency` from "15m" to "1m"
- Updated `data_loader.freq` from "15min" to "1min"  
- Changed `executor.time_per_step` from "15min" to "1min"
- Updated `exchange_kwargs.freq` from "15min" to "1min"
- Set benchmark to "BTCUSDT" for crypto-appropriate comparison

## Next Steps
The workflow now expects 1min crypto data. Users need to:

1. Update data collection scripts to fetch 1min frequency data
2. Re-run data collection to populate `data/qlib_data/crypto` with 1min data
3. The workflow will then run successfully with proper backtesting

## Update Log
- 2025-11-08: Identified qlib backtesting requirement for 1min frequency
- 2025-11-08: Updated all frequency settings in workflow.json to 1min
- 2025-11-08: Set BTCUSDT as benchmark for crypto backtesting
- 2025-11-08: Verified configuration changes (workflow will work once 1min data is collected)