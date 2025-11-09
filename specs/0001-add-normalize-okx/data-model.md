# Data Model: Add Normalize Function to OKX Data Collector

**Date**: 2025-11-08
**Feature**: 001-add-normalize-okx

## KlineRecord Entity

### Structure
```python
KlineRecord = {
    'symbol': str,        # Trading pair (e.g., 'BTC/USDT')
    'timestamp': datetime, # Unix timestamp converted to datetime
    'open': float,        # Opening price
    'high': float,        # Highest price in interval
    'low': float,         # Lowest price in interval
    'close': float,       # Closing price
    'volume': float,      # Trading volume
    'interval': str       # Time interval (e.g., '15m')
}
```

### Validation Rules
- **symbol**: Non-empty string, valid trading pair format
- **timestamp**: Valid datetime object, timezone-naive
- **open/high/low/close**: Non-negative float values
- **volume**: Non-negative float value
- **interval**: Non-empty string (e.g., '15m', '1h')

### Relationships
- None (flat structure for CSV storage)
- Multiple records per symbol form time series
- Records are independent but chronologically ordered

### State Transitions
- **Raw Data**: Initial state from API (timestamp as int/float)
- **Normalized**: After normalization (timestamp as datetime, sorted, deduplicated)
- **Persisted**: Saved to CSV file

### Data Volume Expectations
- Typical dataset: 1000-10000 records per symbol per collection run
- Memory usage: ~1MB per 1000 records
- Storage: ~50KB per 1000 records in CSV format

### Lifecycle
1. **Creation**: Records created from OKX API responses
2. **Normalization**: Processed by `normalize_klines` function
3. **Storage**: Saved to CSV files
4. **Consumption**: Loaded by downstream analysis tools