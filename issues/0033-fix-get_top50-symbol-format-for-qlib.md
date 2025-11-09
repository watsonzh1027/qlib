# 0033-fix-symbol-format-handling-for-multi-module-usage

Status: CLOSED
Created: 2025-11-08 14:00:00

## Problem Description
The `top50_symbols.json` file is used by multiple modules: data collection scripts use CCXT format ("BTC/USDT") for API calls, while qlib workflow requires qlib format ("BTCUSDT"). Initially, we modified the file to qlib format, but this would break data collection.

## Root Cause
Different modules require different symbol formats:
- CCXT-based data collection: "BTC/USDT" 
- Qlib data loading: "BTCUSDT" (no separators)
- The config file serves both purposes

## Solution
Keep `top50_symbols.json` in CCXT format ("BTC/USDT") for data collection compatibility, and handle format conversion in the config manager for qlib usage.

Modified `config_manager.py` in `get_data_handler_config()` to convert symbols from CCXT to qlib format when resolving the `<data.symbols>` placeholder:

```python
elif obj == "<data.symbols>":
    # Convert CCXT symbols to qlib format for qlib compatibility
    ccxt_symbols = self.get_crypto_symbols()
    return [symbol.replace('/', '') for symbol in ccxt_symbols]
```

This ensures:
- Data collection scripts can use CCXT format from config
- Qlib workflow automatically gets qlib-compatible format
- No changes needed to existing data collection code

## Update Log
- 2025-11-08: Reverted top50_symbols.json to CCXT format ("BTC/USDT")
- 2025-11-08: Reverted get_top50.py to save CCXT format
- 2025-11-08: Modified config_manager.py to convert symbols to qlib format during placeholder resolution
- 2025-11-08: Verified workflow still works with automatic format conversion