# Change 0001: Crypto Data Feeder Module

Status: IMPLEMENTATION  
Created: 2025-01-XX  
Author: watson  

# Pointers
- Proposal source: ../../proposals/0001-crypto-data-feeder.md
- Tasks: tasks.md
- Design: design.md (if present)
- Specs: specs/

---

## Changes

### 1. `scripts/get_top50.py`
- Generate `config/instruments.json` instead of `top50_symbols.json`.
- The new file format includes additional metadata for each symbol.

**Updated Output Format**:
```json
{
  "symbols": [
    {
      "symbol": "BTC-USDT",
      "funding_rate": 0.0001,
      "updated_at": "2025-01-05T12:00:00Z"
    },
    {
      "symbol": "ETH-USDT",
      "funding_rate": -0.0002,
      "updated_at": "2025-01-05T12:00:00Z"
    }
  ],
  "count": 50
}
```

---

### 2. Storage Folder Structure
The storage structure has been updated to improve organization and compatibility with Qlib's data structure.

**Updated Storage Structure**:
```text
data/
├── klines/
│   ├── BTC-USDT/
│   │   ├── BTC-USDT_15min.parquet
│   │   └── BTC-USDT_1h.parquet
│   ├── ETH-USDT/
│   │   ├── ETH-USDT_15min.parquet
│   └── ...
├── qlib_data/   # Qlib-compatible binary data
└── funding/
    └── funding_rates_20250105.parquet
```

---

### 3. `scripts/okx_data_collector.py` Workflow
The workflow for the data collector has been updated to align with the new storage structure.

**Updated Workflow**:
1. Fetch OHLCV data for tracked symbols.
2. Save OHLCV data into `data/klines/{symbol}/{symbol}_{interval}.parquet`.
3. Persist funding rate data into `data/funding/funding_rates_{date}.parquet`.
4. Ensure deduplication by `(symbol, timestamp)` during data storage.

---

### 4. `scripts/convert_to_qlib.py` Workflow
The Qlib conversion workflow has been updated to process data from the new storage structure.

**Updated Workflow**:
1. Scan `data/klines/{symbol}/*.parquet` for OHLCV data.
2. Extract unique symbols and merge data by symbol.
3. Deduplicate data by `(symbol, timestamp)`.
4. Convert merged data to Qlib binary format and save in `data/qlib_data/`.

---

### 5. `scripts/sample_backtest.py`
- Updated to use centralized parameter management via `ConfigManager`.
- Parameters are loaded dynamically from `config/workflow.json`.

**Rationale**:
- Simplifies parameter updates across the data pipeline.
- Ensures consistency and reduces hardcoded values.

---

### 6. Module Rework and Retesting
- Due to design modifications, the following modules require updates and retesting:
  - `scripts/get_top50.py`
  - `scripts/okx_data_collector.py`
  - `scripts/convert_to_qlib.py`
  - `scripts/sample_backtest.py`

**Implications**:
- Ensure alignment with the updated design for centralized parameter management and data flow.
- Validate functionality through comprehensive testing.

---

## Summary
The above changes ensure better organization of data, improved compatibility with Qlib, and enhanced workflows for data collection and conversion. All other aspects of the proposal remain unchanged.
