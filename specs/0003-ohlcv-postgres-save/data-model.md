# Data Model: PostgreSQL OHLCV Storage

**Feature**: Save OHLCV Data to PostgreSQL
**Date**: 2025-11-14
**Version**: 1.0

## Overview

This document defines the complete data model for storing OHLCV (Open, High, Low, Close, Volume) cryptocurrency data in PostgreSQL. The design supports high-throughput ingestion, efficient querying, and long-term data retention.

## Core Entities

### OHLCV Data Table

**Primary Entity**: Stores time-series OHLCV data for all cryptocurrency symbols.

```sql
CREATE TABLE ohlcv_data (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Business Keys
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10) NOT NULL,  -- Time interval: '1m', '5m', '15m', '1h', '4h', '1d', etc.
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Price Data (8 decimal precision for crypto)
    open_price DECIMAL(20,8) NOT NULL,
    high_price DECIMAL(20,8) NOT NULL,
    low_price DECIMAL(20,8) NOT NULL,
    close_price DECIMAL(20,8) NOT NULL,

    -- Volume Data
    volume DECIMAL(20,8) NOT NULL,
    quote_volume DECIMAL(20,8),

    -- Additional Metrics
    trade_count INTEGER,
    taker_buy_volume DECIMAL(20,8),
    taker_buy_quote_volume DECIMAL(20,8),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    UNIQUE(symbol, interval, timestamp),
    CHECK (open_price > 0),
    CHECK (high_price > 0),
    CHECK (low_price > 0),
    CHECK (close_price > 0),
    CHECK (open_price > 0),
    CHECK (high_price > 0),
    CHECK (low_price > 0),
    CHECK (close_price > 0),
    CHECK (volume >= 0),
    CHECK (high_price >= open_price),
    CHECK (high_price >= close_price),
    CHECK (low_price <= open_price),
    CHECK (low_price <= close_price)
) PARTITION BY RANGE (timestamp);
```

**Field Descriptions**:
- `symbol`: Cryptocurrency trading pair (e.g., "BTC-USDT", "ETH-BTC")
- `timestamp`: UTC timestamp of the OHLCV candle
- `open_price`: Opening price for the time period
- `high_price`: Highest price during the time period
- `low_price`: Lowest price during the time period
- `close_price`: Closing price for the time period
- `volume`: Trading volume in base currency
- `quote_volume`: Trading volume in quote currency
- `trade_count`: Number of trades in the period
- `taker_buy_volume`: Volume from taker buy orders
- `taker_buy_quote_volume`: Quote volume from taker buy orders

### Partitioning Strategy

**Hybrid Partitioning**: Two-level partitioning by interval then by month for optimal query performance and maintenance.

```sql
-- Main table with interval-based partitioning
CREATE TABLE ohlcv_data (
    -- ... fields including interval
) PARTITION BY LIST (interval);

-- Sub-partitions for each interval by time
-- 1-minute data (high frequency, keep recent data)
CREATE TABLE ohlcv_data_1m PARTITION OF ohlcv_data
    FOR VALUES IN ('1m')
    PARTITION BY RANGE (timestamp);

-- 5-minute data
CREATE TABLE ohlcv_data_5m PARTITION OF ohlcv_data
    FOR VALUES IN ('5m')
    PARTITION BY RANGE (timestamp);

-- 15-minute data
CREATE TABLE ohlcv_data_15m PARTITION OF ohlcv_data
    FOR VALUES IN ('15m')
    PARTITION BY RANGE (timestamp);

-- 1-hour data
CREATE TABLE ohlcv_data_1h PARTITION OF ohlcv_data
    FOR VALUES IN ('1h')
    PARTITION BY RANGE (timestamp);

-- 4-hour data
CREATE TABLE ohlcv_data_4h PARTITION OF ohlcv_data
    FOR VALUES IN ('4h')
    PARTITION BY RANGE (timestamp);

-- 1-day data (long retention)
CREATE TABLE ohlcv_data_1d PARTITION OF ohlcv_data
    FOR VALUES IN ('1d')
    PARTITION BY RANGE (timestamp);

-- Example monthly sub-partitions for 1-minute data
CREATE TABLE ohlcv_data_1m_2024_01 PARTITION OF ohlcv_data_1m
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE ohlcv_data_1m_2024_02 PARTITION OF ohlcv_data_1m
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
```

**Partition Naming Convention**: `ohlcv_data_{interval}_{YYYY_MM}`

**Rationale for Hybrid Partitioning**:
- **Query Optimization**: Most queries filter by specific interval (e.g., "get 1h candles for BTC")
- **Data Lifecycle**: Different intervals have different retention needs (1m data kept shorter than 1d)
- **Performance**: Partition pruning works at both levels
- **Maintenance**: Easier to manage different data lifecycles per interval

## Indexes

### Performance Indexes

```sql
-- Primary key index (automatic)
-- UNIQUE constraint index on (symbol, interval, timestamp)

-- Most common query: specific symbol + interval + time range
CREATE INDEX idx_ohlcv_symbol_interval_timestamp ON ohlcv_data (symbol, interval, timestamp);

-- Symbol + interval filtering (for metadata queries)
CREATE INDEX idx_ohlcv_symbol_interval ON ohlcv_data (symbol, interval);

-- Time-based queries within partitions
CREATE INDEX idx_ohlcv_timestamp ON ohlcv_data (timestamp);

-- Latest data queries (partial index for recent data)
CREATE INDEX idx_ohlcv_recent_1m ON ohlcv_data (symbol, interval, timestamp DESC)
WHERE interval IN ('1m', '5m', '15m') AND timestamp > NOW() - INTERVAL '7 days';

CREATE INDEX idx_ohlcv_recent_hourly ON ohlcv_data (symbol, interval, timestamp DESC)
WHERE interval IN ('1h', '4h') AND timestamp > NOW() - INTERVAL '90 days';

CREATE INDEX idx_ohlcv_recent_daily ON ohlcv_data (symbol, interval, timestamp DESC)
WHERE interval = '1d' AND timestamp > NOW() - INTERVAL '2 years';

-- Interval-specific indexes for common queries
CREATE INDEX idx_ohlcv_1m_symbol_timestamp ON ohlcv_data (symbol, timestamp)
WHERE interval = '1m';

CREATE INDEX idx_ohlcv_1h_symbol_timestamp ON ohlcv_data (symbol, timestamp)
WHERE interval = '1h';

CREATE INDEX idx_ohlcv_1d_symbol_timestamp ON ohlcv_data (symbol, timestamp)
WHERE interval = '1d';
```

### Index Maintenance

- **Reindexing**: Monthly reindexing of active partitions
- **Index Monitoring**: Track index usage and bloat
- **Index Cleanup**: Remove unused indexes based on query patterns

## Data Integrity

### Constraints

**Check Constraints**:
- Price fields must be positive
- High price >= max(open, close)
- Low price <= min(open, close)
- Volume >= 0

**Unique Constraints**:
- `(symbol, interval, timestamp)` prevents duplicate data points for same symbol/interval/time

**Foreign Key Constraints**:
- None (single table design for performance)

### Data Validation Rules

**Business Rules**:
1. Timestamps must be UTC and aligned to candle intervals
2. Symbols must follow exchange-specific formatting
3. Intervals must be valid: '1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'
4. Price precision limited to 8 decimal places
5. Volume data must be non-negative
6. Timestamp must be aligned to interval boundaries (e.g., 1h candles at :00 minutes)

## Relationships

### Entity Relationships

**OHLCV Data** (Central Table)
- No direct relationships (denormalized for performance)
- Implicit relationships through symbol and timestamp groupings

### Data Flow Relationships

```
Data Source (Exchange API)
    ↓
OHLCV Collection (okx_data_collector.py)
    ↓
PostgreSQL Storage (postgres_storage.py)
    ↓
OHLCV Data Table
    ↓
Query Interface (qlib data provider)
    ↓
Analysis & Backtesting
```

## Data Types Rationale

### Precision Requirements

**Cryptocurrency Prices**:
- **Range**: $0.00000001 to $100,000+
- **Precision**: 8 decimal places covers all major cryptocurrencies
- **Storage**: DECIMAL(20,8) = 12 bytes per field

**Volume Data**:
- **Range**: 0 to quadrillions
- **Precision**: 8 decimal places for fractional volumes
- **Storage**: DECIMAL(20,8) same as prices

### Performance Considerations

**Query Performance**:
- DECIMAL operations are 2-3x slower than floating point
- Acceptable for target throughput (< 5000 records/second)
- Precision guarantee outweighs performance cost

**Storage Efficiency**:
- Total row size: ~150 bytes (with all fields)
- Monthly partition: ~4.5MB for 30,000 records
- Annual storage: ~540MB per symbol (conservative estimate)

## Migration Strategy

### Schema Evolution

**Version 1.0** (Current):
- Basic OHLCV fields
- Monthly partitioning
- Essential indexes

**Future Versions** (Extensibility):
- Additional metrics fields
- Multiple timeframe support
- Historical data corrections

### Data Migration

**From CSV to PostgreSQL**:
1. Create target partitions
2. Bulk load historical data
3. Validate data integrity
4. Update indexes and statistics

**Migration Scripts**:
- `migrate_csv_to_postgres.py`: Data migration utility
- `validate_migration.py`: Integrity checking
- Rollback procedures for failed migrations

## Performance Characteristics

### Query Patterns

**Common Queries by Interval**:
1. **High-frequency (1m, 5m)**: Recent data for live trading
   ```sql
   SELECT * FROM ohlcv_data
   WHERE symbol = ? AND interval = '1m' AND timestamp > NOW() - INTERVAL '1 day'
   ORDER BY timestamp DESC
   ```

2. **Medium-frequency (15m, 1h)**: Technical analysis
   ```sql
   SELECT * FROM ohlcv_data
   WHERE symbol = ? AND interval = '1h' AND timestamp BETWEEN ? AND ?
   ```

3. **Low-frequency (1d)**: Long-term analysis
   ```sql
   SELECT * FROM ohlcv_data
   WHERE symbol = ? AND interval = '1d' AND timestamp >= '2020-01-01'
   ```

4. **Metadata queries**: Available intervals and symbols
   ```sql
   SELECT DISTINCT symbol, interval FROM ohlcv_data
   ```

**Optimization Strategies**:
- Partition pruning at both interval and time levels
- Index-only scans for metadata queries
- Parallel query execution for large historical datasets
- Different retention policies per interval

### Ingestion Performance

**Batch Insert Strategy**:
- Batch size: 1000 records
- Transaction size: 10,000 records
- Parallel ingestion: Multiple symbols concurrently

**Performance Targets**:
- 5000 records/second sustained ingestion
- < 100ms batch insert latency
- 99.9% successful ingestion rate

## Monitoring & Maintenance

### Health Checks

**Data Quality Metrics**:
- Duplicate records (should be 0)
- Missing data gaps
- Price anomaly detection
- Volume consistency checks

**Performance Metrics**:
- Query latency percentiles
- Ingestion throughput
- Index bloat percentage
- Partition size distribution

### Maintenance Tasks

**Daily**:
- Update partition statistics for active partitions
- Monitor ingestion performance per interval
- Validate data alignment for each interval

**Weekly**:
- Reindex active partitions (focus on high-frequency intervals)
- Analyze table bloat by interval
- Clean up misaligned timestamps

**Monthly**:
- Create future partitions for all intervals
- Archive old partitions based on retention policy:
  - 1m/5m data: Keep 1 year
  - 15m/1h data: Keep 2 years
  - 1d data: Keep indefinitely
- Review and optimize interval-specific indexes

**Quarterly**:
- Review and optimize indexes by usage patterns
- Update performance baselines per interval
- Assess storage growth trends

## Security Considerations

### Data Protection

**Access Control**:
- Read-only access for analysis users
- Write access restricted to ingestion processes
- Audit logging for all data modifications

**Encryption**:
- Data at rest encryption (optional)
- Secure credential management

### Compliance

**Data Retention**:
- Configurable retention periods
- Automated data purging
- Legal hold capabilities

**Audit Trail**:
- Change tracking via `updated_at` timestamps
- Ingestion source logging
- Access pattern monitoring

## Implementation Notes

### Python Data Types

**Pandas DataFrame Mapping**:
```python
ohlcv_dtypes = {
    'symbol': 'string',
    'interval': 'string',  # '1m', '5m', '1h', '1d', etc.
    'timestamp': 'datetime64[ns, UTC]',
    'open_price': 'float64',
    'high_price': 'float64',
    'low_price': 'float64',
    'close_price': 'float64',
    'volume': 'float64',
    'quote_volume': 'float64',
    'trade_count': 'Int64',
    'taker_buy_volume': 'float64',
    'taker_buy_quote_volume': 'float64'
}
```

### SQLAlchemy Model

**ORM Definition**:
```python
from sqlalchemy import Column, String, DateTime, Numeric, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class OHLCVData(Base):
    __tablename__ = 'ohlcv_data'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    interval = Column(String(10), nullable=False)  # '1m', '5m', '1h', etc.
    timestamp = Column(DateTime(timezone=True), nullable=False)
    open_price = Column(Numeric(20, 8), nullable=False)
    high_price = Column(Numeric(20, 8), nullable=False)
    low_price = Column(Numeric(20, 8), nullable=False)
    close_price = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    quote_volume = Column(Numeric(20, 8))
    trade_count = Column(Integer)
    taker_buy_volume = Column(Numeric(20, 8))
    taker_buy_quote_volume = Column(Numeric(20, 8))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        {'schema': 'crypto'}  # Optional: use a specific schema
    )
```

This data model provides a solid foundation for scalable OHLCV data storage with PostgreSQL, balancing performance, data integrity, and maintainability requirements.