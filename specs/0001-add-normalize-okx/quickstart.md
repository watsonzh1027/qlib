# Quick Start: Normalized OKX Data Collection

**Feature**: 001-add-normalize-okx
**Date**: 2025-11-08

## Prerequisites

1. **Environment Setup**:
   ```bash
   conda activate qlib
   ```

2. **Verify Dependencies**:
   ```bash
   python -c "import pandas as pd; print('pandas version:', pd.__version__)"
   ```

## Running Data Collection with Normalization

### Basic Usage

```bash
cd /home/watson/work/qlib-crypto
python scripts/okx_data_collector.py \
  --start_time 2025-01-01T00:00:00Z \
  --end_time 2025-01-02T00:00:00Z \
  --limit 100
```

### Parameters

- `--start_time`: Start time in ISO format (e.g., 2025-01-01T00:00:00Z)
- `--end_time`: End time in ISO format
- `--limit`: Maximum number of data points per request (default: 100)

## Verifying Normalization

### Check Saved Data

```bash
# List collected symbols
ls data/klines/

# View normalized data for a symbol
head -10 data/klines/BTC_USDT/BTC_USDT.csv
```

### Expected Output Format

```csv
symbol,timestamp,open,high,low,close,volume,interval
BTC/USDT,2025-01-01 00:00:00,50000.0,51000.0,49000.0,50500.0,100.5,15m
BTC/USDT,2025-01-01 00:15:00,50500.0,52000.0,50000.0,51500.0,95.2,15m
```

### Validation Checks

1. **Timestamps are sorted**: Each row's timestamp should be after the previous
2. **No duplicates**: No identical timestamp rows
3. **Datetime format**: Timestamps in YYYY-MM-DD HH:MM:SS format
4. **Data integrity**: All OHLCV values preserved

### Troubleshooting

- **Empty files**: Check if symbol has trading data for the time range
- **Permission errors**: Ensure write access to `data/klines/` directory
- **Import errors**: Verify qlib environment is activated

## Integration with Qlib

After collection, integrate with qlib:

```python
import qlib
qlib.init(provider_uri="data/qlib_data", region="cn")

# Data is now available for analysis
from qlib.data import D
instruments = D.instruments()
print("Available instruments:", instruments)
```