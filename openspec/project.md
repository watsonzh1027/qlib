# Project Specification: qlib-crypto

## Project Overview

**qlib-crypto** is a quantitative cryptocurrency trading research platform that integrates real-time data collection from OKX exchange with Microsoft's Qlib framework for strategy development and backtesting.

### Mission
Provide an automated, open-source pipeline for collecting top-ranked cryptocurrency data (by funding rate) and enabling systematic quantitative research through Qlib.

---

## Tech Stack

### Core Technologies

#### Data Collection Layer
- **cryptofeed** - Real-time cryptocurrency market data collection
  - WebSocket connections to OKX exchange
  - Support for OHLCV candles, funding rates, trades, order books
- **OKX API** - Exchange data source
  - Top 50 coins by funding rate
  - Perpetual swap contracts (SWAP)
  - REST API for metadata, WebSocket for streaming

#### Data Storage
- **Apache Parquet** - Primary data format
  - Columnar storage for efficient querying
  - High compression ratio
  - Native Qlib compatibility
- **Alternative Options**: PostgreSQL, MongoDB (for metadata)

#### Quantitative Framework
- **Qlib** (Microsoft) - Core strategy engine
  - Data provider interface
  - Feature engineering
  - Model training (LightGBM, etc.)
  - Backtesting engine

#### Automation & Scheduling
- **APScheduler** / **cron** - Task scheduling
  - Data collection updates
  - Top 50 symbol refresh (every 8 hours)
  - Daily data format conversion
- **Docker** - Containerization (recommended)
- **systemd/supervisor** - Process management

#### Development Environment
- **Conda** - Python environment management
  - Environment name: `qlib`
  - **CRITICAL**: Must run `conda activate qlib` before all operations

### Language & Tools
- **Python 3.10+**
- **pandas, pyarrow** - Data manipulation
- **requests** - HTTP client for REST APIs
- **asyncio** - Asynchronous data collection

---

## Project Structure

```
qlib-crypto/
├── .github/
│   └── copilot-instructions.md      # AI assistant guidelines
├── .rules/
│   └── ProjectRule.md                # Project conventions
├── openspec/
│   ├── project.md                    # This file
│   └── AGENTS.md                     # OpenSpec integration
├── docs/
│   └── data_feeder.md                # Data collection architecture
├── issues/                           # Issue tracking (markdown files)
│   └── 0001-*.md                     # Sequential issue documentation
├── okx_data/                         # Raw data from OKX
│   ├── kline_1m/                     # 1-minute candles (Parquet)
│   └── funding/                      # Funding rate data
├── qlib_data/                        # Qlib-formatted data
│   ├── instruments/
│   │   └── all.txt                   # Symbol registry
│   ├── features/
│   │   └── day/                      # Feature data (binary)
│   └── calendars/
│       └── cn.txt                    # Trading calendar
├── scripts/
│   ├── okx_data_collector.py         # Real-time data collector
│   ├── get_top50.py                  # Symbol ranking logic
│   └── convert_to_qlib.py            # Data format converter
└── CODING_STANDARDS.md               # Development guidelines
```

---

## Key Conventions

### Environment Management
1. **Always activate qlib environment first**:
   ```bash
   conda activate qlib
   ```
2. Remind in every terminal session or script execution

### Error Handling Protocol
**CRITICAL RULE: ONE ERROR AT A TIME**

- ✅ Fix errors sequentially
- ❌ Never batch-fix unrelated errors
- **Workflow**:
  1. Identify ONE error
  2. Provide fix + test
  3. Wait for user confirmation
  4. Only proceed after explicit approval

### Issue Documentation
- **Location**: `issues/` directory
- **Naming**: `<number>-<description>.md`
  - Example: `0001-fix_chrono_header_issue.md`
  - Sequential numbering from 0001
- **Content Requirements**:
  - Problem description
  - Root cause analysis
  - Solution implemented
  - **Successful steps** (for learning)

---

## Data Pipeline Architecture

### 1. Data Collection
```
OKX WebSocket (cryptofeed)
    ↓
Real-time OHLCV + Funding Rates
    ↓
Local Parquet Storage (by date)
```

**Update Frequency**:
- Candles: Real-time (1-minute bars)
- Funding rates: Every 8 hours
- Top 50 refresh: Every 8 hours

### 2. Symbol Selection Logic
- Rank all OKX perpetual swaps by **absolute funding rate**
- Select top 50 symbols
- Update `top50_symbols.json`
- Restart data collector with new symbols

### 3. Data Transformation
```
Parquet (OHLCV)
    ↓
Merge all symbols
    ↓
Convert to Qlib binary format
    ↓
Update instruments/all.txt
```

### 4. Qlib Integration
```python
qlib.init(provider_uri='qlib_data', region=RegCN)
dataset = D.features(instruments, ['$close', '$volume', ...])
```

---

## File Naming Conventions

### Data Files
- **Candles**: `{SYMBOL}_{DATE}.parquet`
  - Example: `BTC_USDT_20250405.parquet`
- **Funding**: `funding_rates_{DATE}.parquet`

### Issue Files
- **Format**: `{NUMBER}-{description}.md`
- **Number**: 4-digit zero-padded (0001, 0002, ...)
- **Description**: snake_case, descriptive

### Code Files
- Python scripts: `snake_case.py`
- Configuration: `UPPERCASE.md` or `.yaml`

---

## Configuration Management

### Top 50 Symbols
- **File**: `top50_symbols.json`
- **Update**: Every 8 hours via `get_top50.py`
- **Format**: JSON array of symbol strings

### Qlib Configuration
- **Provider URI**: `qlib_data/` (local directory)
- **Region**: `CN` (convention)
- **Instruments**: Auto-generated from collected symbols

---

## Automation Schedule

| Task | Frequency | Script | Purpose |
|------|-----------|--------|---------|
| Symbol ranking | Every 8 hours | `get_top50.py` | Update top 50 list |
| Data collection | Continuous | `okx_data_collector.py` | Real-time candles/funding |
| Format conversion | Daily 00:00 | `convert_to_qlib.py` | Qlib data update |

**Recommended**: Use cron or APScheduler for scheduling

---

## Development Workflow

### Starting a Session
```bash
conda activate qlib
cd /home/watson/work/qlib-crypto
```

### Adding New Features
1. Create proposal in `openspec/` if architectural change
2. Follow one-error-at-a-time protocol
3. Document in `issues/` after resolution

### Testing Changes
1. Test in isolation
2. Get user confirmation
3. Move to next change only with approval

---

## Dependencies

### Python Packages
```txt
cryptofeed>=2.4.0
qlib>=0.9.0
pandas>=2.0.0
pyarrow>=12.0.0
requests>=2.31.0
APScheduler>=3.10.0
```

### System Requirements
- Python 3.10+
- Conda (for environment management)
- Docker (optional, for deployment)
- cron or equivalent task scheduler

---

## Performance Considerations

### Data Retention
- **Raw Parquet**: Keep last 90 days (configurable)
- **Qlib binary**: Full history for backtesting

### Optimization
- Use Parquet partitioning by date
- Deduplicate by `(symbol, timestamp)`
- Compress with snappy codec

### Monitoring
- Log collection lag
- Track missing data points
- Alert on funding rate fetch failures

---

## Future Enhancements

- [ ] Multi-exchange support (Binance, Bybit)
- [ ] Real-time strategy execution (paper trading)
- [ ] Prometheus metrics export
- [ ] Multi-timeframe support (5m, 1h, 1d)
- [ ] Automated model retraining pipeline
- [ ] Web dashboard for monitoring

---

## References

- [Qlib Documentation](https://qlib.readthedocs.io/)
- [cryptofeed GitHub](https://github.com/bmoscon/cryptofeed)
- [OKX API Docs](https://www.okx.com/docs-v5/en/)
- Project Rules: `.rules/ProjectRule.md`
- Coding Standards: `CODING_STANDARDS.md`

---

**Last Updated**: 2025-01-XX  
**Maintainer**: watson  
**License**: [Specify if applicable]
