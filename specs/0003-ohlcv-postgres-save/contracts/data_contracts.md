# OHLCV Data Contracts

**Version**: 1.0
**Date**: 2025-11-14

## Overview

This document defines the data contracts for OHLCV (Open, High, Low, Close, Volume) cryptocurrency data. These contracts ensure data consistency, validation, and interoperability across the entire system.

## Core Data Structures

### OHLCV Record

Fundamental data structure for a single OHLCV candle.

```python
from typing import TypedDict, Optional
from datetime import datetime

class OHLCVRecord(TypedDict, total=False):
    """Single OHLCV data point with optional fields."""

    # Required fields
    symbol: str                    # Trading pair (e.g., "BTC-USDT")
    interval: str                  # Time interval (e.g., "1m", "1h", "1d")
    timestamp: datetime           # Candle timestamp (UTC)
    open_price: float             # Opening price
    high_price: float             # Highest price in interval
    low_price: float              # Lowest price in interval
    close_price: float            # Closing price
    volume: float                 # Trading volume (base currency)

    # Optional fields
    quote_volume: Optional[float]          # Volume in quote currency
    trade_count: Optional[int]             # Number of trades
    taker_buy_volume: Optional[float]      # Taker buy volume
    taker_buy_quote_volume: Optional[float] # Taker buy quote volume
```

### DataFrame Schema

Pandas DataFrame representation used throughout the system.

```python
import pandas as pd

OHLCV_DF_SCHEMA = {
    'symbol': 'string',
    'interval': 'string',
    'timestamp': 'datetime64[ns, UTC]',
    'open_price': 'float64',
    'high_price': 'float64',
    'low_price': 'float64',
    'close_price': 'float64',
    'volume': 'float64',
    'quote_volume': 'float64',
    'trade_count': 'Int64',  # Nullable integer
    'taker_buy_volume': 'float64',
    'taker_buy_quote_volume': 'float64'
}
```

## Field Specifications

### Symbol Field

**Type**: `str`
**Format**: `{BASE}-{QUOTE}` (e.g., "BTC-USDT", "ETH-BTC")
**Constraints**:
- Must contain exactly one hyphen
- Base and quote currencies must be 2-10 uppercase letters
- No spaces or special characters except hyphen
**Validation**:
```python
import re
SYMBOL_PATTERN = re.compile(r'^[A-Z]{2,10}-[A-Z]{2,10}$')

def validate_symbol(symbol: str) -> bool:
    return bool(SYMBOL_PATTERN.match(symbol))
```

### Interval Field

**Type**: `str`
**Allowed Values**:
- `"1m"`, `"5m"`, `"15m"`, `"30m"` (minutes)
- `"1h"`, `"2h"`, `"4h"`, `"6h"`, `"8h"`, `"12h"` (hours)
- `"1d"`, `"3d"` (days)
- `"1w"` (week)
- `"1M"` (month)

**Validation**:
```python
VALID_INTERVALS = {
    '1m', '5m', '15m', '30m',
    '1h', '2h', '4h', '6h', '8h', '12h',
    '1d', '3d', '1w', '1M'
}

def validate_interval(interval: str) -> bool:
    return interval in VALID_INTERVALS
```

### Timestamp Field

**Type**: `datetime` (timezone-aware)
**Timezone**: UTC only
**Constraints**:
- Must be aligned to interval boundaries
- No future timestamps (max 1 minute in future for real-time data)
- No timestamps before 2010-01-01

**Validation**:
```python
from datetime import datetime, timezone

def validate_timestamp(timestamp: datetime, interval: str) -> bool:
    """Check if timestamp is aligned to interval boundary."""
    if timestamp.tzinfo != timezone.utc:
        return False

    # Convert interval to seconds
    interval_seconds = parse_interval_seconds(interval)

    # Check alignment
    epoch_time = timestamp.timestamp()
    return epoch_time % interval_seconds == 0

def parse_interval_seconds(interval: str) -> int:
    """Convert interval string to seconds."""
    unit = interval[-1]
    value = int(interval[:-1])

    multipliers = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800, 'M': 2592000}
    return value * multipliers[unit]
```

### Price Fields

**Fields**: `open_price`, `high_price`, `low_price`, `close_price`
**Type**: `float`
**Precision**: 8 decimal places maximum
**Range**: `0 < price < 1,000,000`
**Constraints**:
- Must be positive
- High >= max(open, close)
- Low <= min(open, close)

**Validation**:
```python
def validate_prices(record: OHLCVRecord) -> bool:
    """Validate OHLC price relationships."""
    prices = [record['open_price'], record['high_price'],
              record['low_price'], record['close_price']]

    # All positive
    if not all(p > 0 for p in prices):
        return False

    # High/low relationships
    high, low = record['high_price'], record['low_price']
    open_, close = record['open_price'], record['close_price']

    return high >= max(open_, close) and low <= min(open_, close)
```

### Volume Fields

**Fields**: `volume`, `quote_volume`, `taker_buy_volume`, `taker_buy_quote_volume`
**Type**: `float` or `None`
**Range**: `volume >= 0`
**Constraints**:
- Must be non-negative when present
- `taker_buy_volume <= volume` (if both present)
- `taker_buy_quote_volume <= quote_volume` (if both present)

### Trade Count Field

**Type**: `int` or `None`
**Range**: `trade_count >= 0`
**Constraints**:
- Must be non-negative when present

## Data Validation Rules

### Record-Level Validation

```python
def validate_ohlcv_record(record: OHLCVRecord) -> List[str]:
    """
    Validate a single OHLCV record.

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Required fields
    required_fields = ['symbol', 'interval', 'timestamp',
                      'open_price', 'high_price', 'low_price', 'close_price', 'volume']

    for field in required_fields:
        if field not in record or record[field] is None:
            errors.append(f"Missing required field: {field}")

    if errors:
        return errors

    # Field validations
    if not validate_symbol(record['symbol']):
        errors.append(f"Invalid symbol format: {record['symbol']}")

    if not validate_interval(record['interval']):
        errors.append(f"Invalid interval: {record['interval']}")

    if not validate_timestamp(record['timestamp'], record['interval']):
        errors.append(f"Timestamp not aligned to {record['interval']} interval")

    if not validate_prices(record):
        errors.append("Invalid OHLC price relationships")

    # Volume validations
    if record['volume'] < 0:
        errors.append("Volume must be non-negative")

    # Optional field validations
    if 'quote_volume' in record and record['quote_volume'] is not None:
        if record['quote_volume'] < 0:
            errors.append("Quote volume must be non-negative")

    if 'trade_count' in record and record['trade_count'] is not None:
        if record['trade_count'] < 0:
            errors.append("Trade count must be non-negative")

    return errors
```

### DataFrame-Level Validation

```python
def validate_ohlcv_dataframe(df: pd.DataFrame) -> List[str]:
    """
    Validate OHLCV DataFrame.

    Returns:
        List of validation error messages
    """
    errors = []

    # Schema validation
    expected_columns = set(OHLCV_DF_SCHEMA.keys())
    actual_columns = set(df.columns)

    missing_cols = expected_columns - actual_columns
    if missing_cols:
        errors.append(f"Missing columns: {missing_cols}")

    extra_cols = actual_columns - expected_columns
    if extra_cols:
        errors.append(f"Unexpected columns: {extra_cols}")

    # Data type validation
    if 'timestamp' in df.columns:
        if not pd.api.types.is_datetime64tz_dtype(df['timestamp']):
            errors.append("timestamp column must be timezone-aware datetime")
        elif df['timestamp'].dt.tz != timezone.utc:
            errors.append("timestamp must be UTC timezone")

    # Record-level validation for sample
    sample_size = min(100, len(df))  # Validate up to 100 records
    for i, row in df.head(sample_size).iterrows():
        record = row.to_dict()
        record_errors = validate_ohlcv_record(record)
        if record_errors:
            errors.extend([f"Row {i}: {err}" for err in record_errors])

    return errors
```

## Data Transformation Contracts

### CSV to DataFrame

```python
def csv_to_ohlcv_df(csv_path: str, symbol: str, interval: str) -> pd.DataFrame:
    """
    Convert CSV file to standardized OHLCV DataFrame.

    Expected CSV format (Binance/OKX style):
    timestamp,open,high,low,close,volume,quote_volume,trade_count,taker_buy_volume,taker_buy_quote_volume

    Returns:
        DataFrame conforming to OHLCV_DF_SCHEMA
    """
    df = pd.read_csv(csv_path)

    # Standardize column names
    column_mapping = {
        'timestamp': 'timestamp',
        'open': 'open_price',
        'high': 'high_price',
        'low': 'low_price',
        'close': 'close_price',
        'volume': 'volume'
    }
    df = df.rename(columns=column_mapping)

    # Add required fields
    df['symbol'] = symbol
    df['interval'] = interval

    # Convert timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

    # Ensure schema compliance
    for col, dtype in OHLCV_DF_SCHEMA.items():
        if col in df.columns:
            df[col] = df[col].astype(dtype)

    return df
```

### API Response to DataFrame

```python
def api_response_to_ohlcv_df(response_data: List[List], symbol: str, interval: str) -> pd.DataFrame:
    """
    Convert exchange API response to OHLCV DataFrame.

    Expected response format (Binance API):
    [
        [timestamp_ms, open, high, low, close, volume, close_time, quote_volume, trade_count, ...]
    ]
    """
    columns = ['timestamp', 'open_price', 'high_price', 'low_price', 'close_price',
               'volume', 'close_time', 'quote_volume', 'trade_count',
               'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']

    df = pd.DataFrame(response_data, columns=columns)

    # Convert timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

    # Add required fields
    df['symbol'] = symbol
    df['interval'] = interval

    # Clean up
    df = df.drop(columns=['close_time', 'ignore'])

    # Convert types
    for col, dtype in OHLCV_DF_SCHEMA.items():
        if col in df.columns:
            df[col] = df[col].astype(dtype)

    return df
```

## Data Quality Contracts

### Completeness Checks

```python
def check_data_completeness(df: pd.DataFrame, interval: str) -> Dict[str, Any]:
    """
    Check for gaps and completeness in OHLCV data.

    Returns:
        Dict with completeness metrics and gap analysis
    """
    if df.empty:
        return {'complete': False, 'gaps': [], 'coverage_percent': 0}

    df = df.sort_values('timestamp')
    interval_seconds = parse_interval_seconds(interval)

    # Calculate expected timestamps
    start_time = df['timestamp'].min()
    end_time = df['timestamp'].max()
    expected_timestamps = pd.date_range(
        start=start_time, end=end_time,
        freq=f'{interval_seconds}S', tz='UTC'
    )

    # Find gaps
    actual_timestamps = set(df['timestamp'])
    gaps = [ts for ts in expected_timestamps if ts not in actual_timestamps]

    coverage = len(df) / len(expected_timestamps)

    return {
        'complete': len(gaps) == 0,
        'gaps': gaps,
        'coverage_percent': coverage * 100,
        'total_expected': len(expected_timestamps),
        'total_actual': len(df)
    }
```

### Consistency Checks

```python
def check_data_consistency(df: pd.DataFrame) -> List[str]:
    """
    Check for data consistency issues.

    Returns:
        List of consistency violation messages
    """
    issues = []

    # Check for duplicate timestamps
    duplicates = df[df.duplicated(['symbol', 'interval', 'timestamp'])]
    if not duplicates.empty:
        issues.append(f"Found {len(duplicates)} duplicate timestamp records")

    # Check for price anomalies (price changes > 50% between consecutive candles)
    df_sorted = df.sort_values('timestamp')
    price_changes = df_sorted['close_price'].pct_change().abs()
    anomalies = price_changes > 0.5
    if anomalies.any():
        issues.append(f"Found {anomalies.sum()} price change anomalies (>50%)")

    # Check volume consistency
    zero_volume = (df['volume'] == 0).sum()
    if zero_volume > 0:
        issues.append(f"Found {zero_volume} records with zero volume")

    return issues
```

## Serialization Contracts

### JSON Serialization

```python
def ohlcv_record_to_json(record: OHLCVRecord) -> str:
    """Serialize OHLCV record to JSON with proper type handling."""
    # Ensure timestamp is ISO format
    if isinstance(record['timestamp'], datetime):
        record = record.copy()
        record['timestamp'] = record['timestamp'].isoformat()

    return json.dumps(record, default=str, sort_keys=True)

def json_to_ohlcv_record(json_str: str) -> OHLCVRecord:
    """Deserialize JSON to OHLCV record."""
    data = json.loads(json_str)

    # Parse timestamp
    if 'timestamp' in data:
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])

    return data
```

### Binary Serialization (Optional)

For high-performance storage or network transfer:

```python
import pickle
import msgpack

def serialize_ohlcv_batch(records: List[OHLCVRecord]) -> bytes:
    """Serialize batch of OHLCV records using MessagePack."""
    # Convert datetime to timestamp for efficient storage
    serializable = []
    for record in records:
        rec = record.copy()
        if isinstance(rec['timestamp'], datetime):
            rec['timestamp'] = rec['timestamp'].timestamp()
        serializable.append(rec)

    return msgpack.packb(serializable)

def deserialize_ohlcv_batch(data: bytes) -> List[OHLCVRecord]:
    """Deserialize batch of OHLCV records."""
    records = msgpack.unpackb(data)

    # Convert timestamps back to datetime
    for record in records:
        if 'timestamp' in record:
            record['timestamp'] = datetime.fromtimestamp(record['timestamp'], tz=timezone.utc)

    return records
```

## Version Compatibility

### Schema Evolution

- **v1.0**: Initial schema with core OHLCV fields
- **Additive Changes**: New optional fields can be added
- **Type Changes**: Must maintain backward compatibility
- **Breaking Changes**: Require version negotiation

### Migration Contracts

When schema changes are needed:

```python
def migrate_ohlcv_record(record: OHLCVRecord, from_version: str, to_version: str) -> OHLCVRecord:
    """
    Migrate OHLCV record between schema versions.

    Handles:
    - Field additions (with defaults)
    - Field renames
    - Type conversions
    - Field removals (with data preservation)
    """
    # Implementation handles version-specific migrations
    pass
```

This comprehensive data contract ensures data consistency, validation, and interoperability across all components of the OHLCV storage system.