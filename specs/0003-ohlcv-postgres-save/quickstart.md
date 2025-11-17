# Quick Start: PostgreSQL OHLCV Storage

**Feature**: Save OHLCV Data to PostgreSQL
**Date**: 2025-11-14
**Version**: 1.0

## Overview

This guide provides a quick start for using the PostgreSQL OHLCV storage system. The implementation supports multiple time intervals (1m, 5m, 1h, 1d, etc.) with optimized partitioning and indexing for high-performance queries.

## Prerequisites

- PostgreSQL 13+
- Python 3.12+
- Required packages: `psycopg2-binary`, `sqlalchemy`, `pandas`

## Installation

```bash
1885  sudo apt upgrade
 1886  sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
 1887  curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
 1888  sudo apt update
 1889  sudo apt upgrade
 1890  sudo apt  install postgresql-18
 1891  sudo systemctl start postgresql
 1892  sudo systemctl enable postgresql
 1893  sudo systemctl status postgresql
 1894  history

# Install dependencies
pip install psycopg2-binary sqlalchemy pandas

# Activate qlib environment (if using conda)
conda activate qlib
```

## Database Setup

### 1. Create Database and User

```sql
-- Create database
CREATE DATABASE qlib_crypto;

-- Create user with proper permissions
CREATE USER crypto_user WITH ENCRYPTED PASSWORD 'change_me_in_production';
GRANT ALL PRIVILEGES ON DATABASE qlib_crypto TO crypto_user;

-- Connect to the database
\c qlib_crypto

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO crypto_user;
```

### 1a. Configure Password Authentication (Important!)

By default, PostgreSQL may use `peer` authentication, which can cause connection errors. You need to enable password-based authentication.

1.  **Find `pg_hba.conf`**:
    ```bash
    sudo -u postgres psql -c 'SHOW hba_file;'
    ```
2.  **Edit the file** (e.g., `sudo nano /etc/postgresql/16/main/pg_hba.conf`):
    Change the `local` connection method from `peer` to `md5`:
    ```conf
    # "local" is for Unix domain socket connections only
    local   all             all                                     md5
    ```
3.  **Restart PostgreSQL**:
    ```bash
    sudo systemctl restart postgresql
    ```
```

### 2. Run Schema Migration

```bash
# Run the database schema setup script
python scripts/setup_postgres_schema.py
```

This creates:
- Main `ohlcv_data` table with hybrid partitioning
- Partitions for common intervals (1m, 5m, 15m, 1h, 4h, 1d)
- Optimized indexes for query performance
- Monthly sub-partitions for recent data

## Configuration

### Environment Variables

```bash
# PostgreSQL connection
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=qlib_crypto
export POSTGRES_USER=crypto_user
export POSTGRES_PASSWORD=your_secure_password
```

### Python Configuration

```python
from dataclasses import dataclass

@dataclass
class PostgresConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "qlib_crypto"
    user: str = "crypto_user"
    password: str = "your_secure_password"

    # Performance tuning
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30

    # Supported intervals
    supported_intervals: list = ("1m", "5m", "15m", "1h", "4h", "1d")

# Create config instance
config = PostgresConfig()
```

## Basic Usage

### 1. Initialize Storage

```python
from scripts.postgres_storage import PostgreSQLStorage

# Initialize with configuration
storage = PostgreSQLStorage.from_config(config)

# Or with connection string
conn_string = "postgresql://crypto_user:password@localhost:5432/qlib_crypto"
storage = PostgreSQLStorage(conn_string)
```

### 2. Save OHLCV Data

```python
import pandas as pd
from datetime import datetime

# Sample OHLCV data
data = pd.DataFrame({
    'timestamp': pd.date_range('2024-01-01', periods=100, freq='1H', tz='UTC'),
    'open': [50000 + i*10 for i in range(100)],
    'high': [50100 + i*10 for i in range(100)],
    'low': [49900 + i*10 for i in range(100)],
    'close': [50050 + i*10 for i in range(100)],
    'volume': [100 + i for i in range(100)],
    'symbol': 'BTC-USDT',
    'interval': '1h'  # Important: specify interval
})

# Save to PostgreSQL
success = storage.save_ohlcv_data(data, symbol='BTC-USDT', interval='1h')
print(f"Data saved: {success}")
```

### 3. Query OHLCV Data

```python
from datetime import datetime, timedelta

# Query specific time range
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 1, 7)

df = storage.get_ohlcv_data(
    symbol='BTC-USDT',
    interval='1h',
    start_date=start_date,
    end_date=end_date
)

print(f"Retrieved {len(df)} records")
print(df.head())
```

### 4. Get Latest Data

```python
# Get latest timestamp for a symbol/interval
latest_time = storage.get_latest_timestamp('BTC-USDT', '1h')
print(f"Latest data timestamp: {latest_time}")

# Get available intervals for a symbol
intervals = storage.get_available_intervals('BTC-USDT')
print(f"Available intervals: {intervals}")
```

## Advanced Usage

### Bulk Insert for High Performance

```python
# Prepare bulk data (list of dicts)
bulk_data = [
    {
        'symbol': 'BTC-USDT',
        'interval': '1m',
        'timestamp': datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        'open_price': 50000.00,
        'high_price': 50100.00,
        'low_price': 49900.00,
        'close_price': 50050.00,
        'volume': 100.50,
        'quote_volume': 5000000.00,
        'trade_count': 150,
        'taker_buy_volume': 60.25,
        'taker_buy_quote_volume': 3000000.00
    },
    # ... more records
]

# Bulk insert (handles duplicates gracefully)
inserted_count = storage.bulk_insert(bulk_data)
print(f"Inserted {inserted_count} records")
```

### Working with Multiple Intervals

```python
# Save data for different intervals
intervals_data = {
    '1m': btc_1m_data,
    '5m': btc_5m_data,
    '1h': btc_1h_data,
    '1d': btc_1d_data
}

for interval, data in intervals_data.items():
    storage.save_ohlcv_data(data, symbol='BTC-USDT', interval=interval)
    print(f"Saved {interval} data")
```

### Integration with Existing Scripts

```python
# Modify existing okx_data_collector.py to use PostgreSQL
from scripts.postgres_storage import PostgreSQLStorage

# In your data collection script
def collect_and_save(symbol, interval):
    # Collect data (existing logic)
    data = collect_ohlcv_data(symbol, interval)

    # Save to PostgreSQL instead of CSV
    storage = PostgreSQLStorage.from_env()
    storage.save_ohlcv_data(data, symbol=symbol, interval=interval)

    print(f"Saved {len(data)} {interval} records for {symbol}")

# Usage
collect_and_save('BTC-USDT', '1h')
collect_and_save('ETH-USDT', '1d')
```

## Performance Tips

### Ingestion Optimization

1. **Batch Size**: Use batches of 1000-5000 records for optimal throughput
2. **Connection Pooling**: Configured automatically with optimized settings
3. **Duplicate Handling**: Uses `ON CONFLICT DO NOTHING` for idempotent inserts

### Query Optimization

1. **Partition Pruning**: Queries automatically benefit from interval-based partitioning
2. **Index Usage**: Composite indexes on `(symbol, interval, timestamp)` optimize common queries
3. **Time Ranges**: Always specify both start and end dates for best performance

### Monitoring

```python
# Health check
is_healthy = storage.health_check()
print(f"Database healthy: {is_healthy}")

# Monitor performance (implement in your monitoring system)
# - Query latency percentiles
# - Ingestion throughput
# - Connection pool utilization
# - Partition sizes by interval
```

## Troubleshooting

### Common Issues

**Connection Failed**:
```python
# Check connection string and credentials
try:
    storage = PostgreSQLStorage(conn_string)
    storage.health_check()
except Exception as e:
    print(f"Connection error: {e}")
    # Check POSTGRES_* environment variables
```

**Duplicate Key Errors**:
- The system automatically handles duplicates using `ON CONFLICT DO NOTHING`
- Check your data for duplicate timestamps within the same symbol/interval

**Slow Queries**:
- Ensure you're using the correct interval in queries
- Check that partitions exist for your date range
- Consider adding more specific indexes if needed

**Out of Memory**:
- Reduce batch sizes for bulk inserts
- Monitor connection pool usage
- Consider increasing PostgreSQL memory settings

### Data Validation

```python
# Validate data before insertion
def validate_ohlcv_data(df):
    required_cols = ['timestamp', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']

    # Check required columns
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Check data types
    if not pd.api.types.is_datetime64tz_dtype(df['timestamp']):
        raise ValueError("timestamp must be timezone-aware datetime")

    # Check price relationships
    invalid_prices = df[df['high_price'] < df['low_price']]
    if not invalid_prices.empty:
        raise ValueError("high_price must be >= low_price")

    return True

# Use validation
if validate_ohlcv_data(data):
    storage.save_ohlcv_data(data, symbol='BTC-USDT', interval='1h')
```

## Migration from CSV

If you have existing CSV data, use the migration script:

```bash
# Migrate CSV files to PostgreSQL
python scripts/migrate_csv_to_postgres.py \
    --csv-dir ./data/klines \
    --symbol BTC-USDT \
    --interval 1h

# Validate migration
python scripts/validate_migration.py \
    --symbol BTC-USDT \
    --interval 1h
```

## Next Steps

1. **Explore Advanced Features**:
   - Custom retention policies per interval
   - Automated partition management
   - Query result caching

2. **Integration**:
   - Connect with qlib data providers
   - Set up monitoring and alerting
   - Configure backup and recovery

3. **Optimization**:
   - Performance tuning based on your workload
   - Index optimization for specific query patterns
   - Connection pool sizing

For detailed API documentation, see `contracts/` directory.
For troubleshooting guides, check the main project documentation.