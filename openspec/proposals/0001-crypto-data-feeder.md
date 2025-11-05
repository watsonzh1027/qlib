# Proposal 0001: Crypto Data Feeder Module

**Status**: IMPLEMENTATION  
**Created**: 2025-01-XX  
**Author**: watson  
**Related Docs**: `docs/data_feeder.md`

---

## Summary

Add a comprehensive data collection module that automatically fetches real-time cryptocurrency data from OKX exchange (top 50 coins by funding rate) using `ccxt` and `ccxtpro`, stores it locally in Parquet format, and converts it to Qlib-compatible format for quantitative strategy research. Includes both scheduled updates and an on-demand update method for immediate data fetching.

---

## Motivation

Currently, the project lacks an automated data pipeline. Manual data collection is:
- **Time-consuming**: Requires manual downloads and format conversions
- **Error-prone**: Missing data points, format inconsistencies
- **Not scalable**: Cannot track dynamic top 50 rankings by funding rate
- **Incomplete**: No integration with Qlib's data provider system

This proposal establishes a production-ready data pipeline that enables:
1. **Automated collection** of high-quality crypto data
2. **Dynamic symbol selection** based on funding rate rankings
3. **Seamless Qlib integration** for strategy backtesting
4. **Fault-tolerant operation** with monitoring and recovery
5. **On-demand updates** for real-time data needs

---

## Goals

### Primary Goals
- ✅ Collect 15-minute OHLCV candles for top 50 coins (by funding rate)
- ✅ Collect funding rate data every 8 hours
- ✅ Auto-refresh top 50 symbol list every 8 hours
- ✅ Store data in efficient Parquet format
- ✅ Convert to Qlib binary format daily
- ✅ Generate Qlib instruments registry automatically
- ✅ Provide on-demand update method for immediate data fetching

### Non-Goals (Future Work)
- ❌ Multi-exchange support (Binance, Bybit) - deferred to v2
- ❌ Real-time strategy execution - out of scope
- ❌ Web dashboard for monitoring - separate proposal needed
- ❌ Historical data backfill - manual process initially

---

## Design

### Architecture Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                     Data Collection Layer                    │
├─────────────────────────────────────────────────────────────┤
│  OKX API via CCXT          │  OKX WebSocket (ccxtpro)        │
│  - Fetch funding rates     │  - Real-time candles (15m)      │
│  - Rank by abs(FR)         │  - Funding rate updates         │
│  - Select top 50           │  - On-demand latest data        │
└──────────┬──────────────┴──────────────┬────────────────────┘
           │                             │
           ▼                             ▼
    ┌─────────────┐              ┌──────────────┐
    │ top50.json  │              │ Parquet Files│
    │ (symbols)   │              │ (okx_data/)  │
    └─────────────┘              └──────┬───────┘
                                        │
                                        ▼
                         ┌──────────────────────────┐
                         │  Conversion Layer        │
                         │  - Merge by symbol       │
                         │  - Deduplicate           │
                         │  - Format transform      │
                         └──────────┬───────────────┘
                                    │
                                    ▼
                         ┌──────────────────────────┐
                         │  Qlib Data Provider      │
                         │  - instruments/all.txt   │
                         │  - features/*.bin        │
                         │  - calendars/cn.txt      │
                         └──────────────────────────┘
```

### Component Design

#### 1. Top 50 Symbol Selector (`scripts/get_top50.py`)

**Responsibility**: Fetch all OKX perpetual swaps funding rates via CCXT, rank by absolute funding rate, select top 50.

**Key Functions**:
```python
def get_okx_funding_top50() -> List[str]:
    """
    Returns: ['BTC-USDT', 'ETH-USDT', ...] (50 symbols)
    """
    
def save_symbols(symbols: List[str], path: str):
    """Save to top50_symbols.json"""
    
def load_symbols(path: str) -> List[str]:
    """Load from top50_symbols.json"""
```

**Update Frequency**: Every 8 hours (via cron)

**Output Format**:
```json
{
  "symbols": ["BTC-USDT", "ETH-USDT", ...],
  "updated_at": "2025-01-05T12:00:00Z",
  "count": 50
}
```

---

#### 2. Real-time Data Collector (`scripts/okx_data_collector.py`)

**Responsibility**: Subscribe to OKX WebSocket feeds via `ccxtpro`, persist to Parquet. Includes on-demand update capability.

**Key Features**:
- Async event-driven architecture (uses `asyncio`)
- Auto-reconnect on connection loss
- In-memory buffering; flush at the end of each 15m candle (or every 4 candles for hourly batch)
- Graceful shutdown (save pending data)
- **On-demand update method**: Fetch latest data immediately when called

**Data Channels**:
1. **OHLCV** (15-minute) - Primary
2. **Funding Rate** - Every 8 hours
3. **Trades** (Optional) - For tick reconstruction

**On-Demand Update Method**:
```python
def update_latest_data(symbols: List[str] = None) -> Dict[str, pd.DataFrame]:
    """
    Fetch latest 15m candles for specified symbols (or all top50 if None).
    Update local Parquet files and return data for immediate use.
    
    Returns: {'BTC-USDT': df, 'ETH-USDT': df, ...}
    """
```

**Storage Structure**:
```text
okx_data/
├── kline_15m/
│   ├── BTC-USDT_20250105.parquet
│   ├── ETH-USDT_20250105.parquet
│   └── ...
└── funding/
    └── funding_rates_20250105.parquet
```

**Schema (OHLCV)**:
```python
{
    'symbol': str,          # BTC-USDT
    'timestamp': int64,     # Unix timestamp (seconds)
    'open': float64,
    'high': float64,
    'low': float64,
    'close': float64,
    'volume': float64,
    'interval': str         # '15m'
}
```

**Process Management**:
- Use `systemd` service or `supervisor`
- Auto-restart on crash
- Log rotation (daily)

---

#### 3. Qlib Format Converter (`scripts/convert_to_qlib.py`)

**Responsibility**: Transform Parquet files to Qlib binary format.

**Workflow**:
1. Scan `okx_data/kline_15m/*.parquet`
2. Extract unique symbols
3. Merge all dates per symbol
4. Deduplicate by `(symbol, timestamp)`
5. Generate `instruments/all.txt`
6. Dump to Qlib binary format (`features/day/*.bin`)

**Qlib Instruments Format** (`instruments/all.txt`):
```text
BTCUSDT	BTC-USDT	SH000000
ETHUSDT	ETH-USDT	SH000000
...
```

**Execution Schedule**: Daily at 00:05 (after market data settled)

---

### Data Flow Diagram

```text
[Every 8h] scripts/get_top50.py
     ↓ (updates)
  config/instruments.json
     ↓ (reads)
[Continuous] scripts/okx_data_collector.py
     ↓ (writes)
  data/klines/{symbol}/{symbol}_15m.parquet
     ↓ (reads)
[Daily 00:05] scripts/convert_to_qlib.py
     ↓ (writes)
  data/qlib_data/features/*.bin
     ↓ (reads)
[On-demand] Qlib Strategy Scripts
     ↓ (calls)
[Immediate] update_latest_data()
     ↓ (updates)
  data/klines/{symbol}/{symbol}_15m.parquet
```

---

## Implementation Plan

### Phase 1: Core Data Collection (Week 1)
- [x] Implement `scripts/get_top50.py` with OKX API integration (via CCXT)
- [x] Write unit tests for symbol selection logic
- [ ] Create `scripts/okx_data_collector.py` with ccxtpro
- [ ] Add Parquet storage with proper schema
- [ ] Implement `update_latest_data()` method for on-demand fetching
- [ ] Test with 5 symbols for 24 hours

**Deliverables**:
- Working data collector with on-demand update
- 24h of sample data
- Basic error handling

---

## File Changes

### New Files

```text
scripts/
├── get_top50.py              # Symbol selector
├── okx_data_collector.py     # Real-time collector with update method
├── convert_to_qlib.py        # Format converter
└── utils/
    ├── __init__.py
    ├── okx_api.py            # OKX REST client wrapper
    └── storage.py            # Parquet I/O helpers

config/
├── collector.yaml            # Collector configuration
└── top50_symbols.json        # Current top 50 list

systemd/
└── okx-collector.service     # systemd service file

tests/
├── test_get_top50.py
├── test_collector.py
├── test_update_method.py     # Test on-demand update
└── test_converter.py
```

### Modified Files

```text
requirements.txt              # Add cryptofeed, pyarrow, ccxt, ccxtpro
README.md                     # Add setup instructions
docs/data_feeder.md           # Mark as implemented
```

---

## Dependencies

### New Python Packages
```txt
cryptofeed>=2.4.0
pyarrow>=12.0.0
requests>=2.31.0
ccxt>=4.0.0
ccxtpro>=1.0.0
pyyaml>=6.0
APScheduler>=3.10.0  # Optional: for in-process scheduling
```

### System Requirements
- Python 3.10+
- 10GB disk space (for 90 days data)
- Stable internet connection
- systemd or supervisor (for process management)

---

## References

- [CCXT Pro Documentation](https://github.com/ccxt/ccxt/wiki/ccxt.pro)
- [OKX API v5 Docs](https://www.okx.com/docs-v5/en/)
- [Qlib Data Provider Guide](https://qlib.readthedocs.io/en/latest/component/data.html)
- [Apache Parquet Format](https://parquet.apache.org/docs/)
- Original Design: `docs/data_feeder.md`

---

**Notes**:
- This proposal follows OpenSpec format
- Implementation will follow project rules (conda activate qlib, one error at a time)
- All issues will be documented in `issues/` directory with sequential numbering
