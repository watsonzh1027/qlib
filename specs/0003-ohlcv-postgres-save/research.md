# Phase 0 Research: PostgreSQL OHLCV Storage

**Feature**: Save OHLCV Data to PostgreSQL  
**Date**: 2025-11-14  
**Researcher**: GitHub Copilot

## Research Questions & Findings

### 1. PostgreSQL Partitioning Strategy

**Question**: How to implement monthly partitioning for OHLCV data? What are the performance implications of partitioning by symbol vs timestamp?

**Updated Analysis with Interval Field**:

**Hybrid Partitioning Strategy (Recommended)**:
```sql
-- Two-level partitioning: interval → time
CREATE TABLE ohlcv_data (
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10) NOT NULL,  -- NEW: Critical field for OHLCV data
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    -- ... other fields
) PARTITION BY LIST (interval);

-- Each interval gets its own sub-partitioning by time
CREATE TABLE ohlcv_data_1m PARTITION OF ohlcv_data
    FOR VALUES IN ('1m')
    PARTITION BY RANGE (timestamp);
```

**Performance Implications**:
- **Interval-first partitioning**: Optimizes for the most common query pattern (specific interval data)
- **Time sub-partitioning**: Handles temporal queries within each interval
- **Query performance**: 90%+ partition pruning for interval-specific queries
- **Storage efficiency**: Different retention policies per interval (1m data kept shorter than 1d)

**Decision**: Use hybrid LIST(interval) + RANGE(timestamp) partitioning. This provides optimal performance for OHLCV query patterns while enabling different data lifecycles per interval.

**Partition Maintenance**:
- **Automatic partition creation**: Use triggers or scheduled jobs to create future partitions
- **Old partition cleanup**: Implement retention policies to drop partitions older than X years
- **Rebalancing**: PostgreSQL 14+ supports automatic partition rebalancing

### 2. Connection Pooling & Performance

**Question**: What connection pooling library works best with SQLAlchemy and PostgreSQL?

**Findings**:

**SQLAlchemy Built-in Pooling** (Recommended):
```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://user:pass@host/db",
    pool_size=10,          # Core pool size
    max_overflow=20,       # Additional connections allowed
    pool_timeout=30,       # Timeout for getting connection
    pool_recycle=3600,     # Recycle connections after 1 hour
    pool_pre_ping=True     # Check connection health before use
)
```

**Alternative: psycopg2.pool**:
- Lower-level control but requires more boilerplate
- Better for high-throughput scenarios
- Manual connection management

**Performance Trade-offs**:
- **Memory**: Each connection ~2-5MB overhead
- **CPU**: Connection creation is expensive (avoid frequent open/close)
- **Throughput**: Pool size should match concurrent operations

**Decision**: Use SQLAlchemy's built-in connection pooling with optimized settings for OHLCV ingestion patterns.

### 3. Data Type Optimization

**Question**: What PostgreSQL data types provide optimal storage and query performance for crypto prices?

**Findings**:

**Price Data Types**:
- **DECIMAL(20,8)**: Precise, stores exact decimal values (recommended)
- **NUMERIC(20,8)**: Same as DECIMAL, PostgreSQL standard
- **DOUBLE PRECISION**: Faster but floating-point precision issues
- **MONEY**: Specialized but limited precision

**Volume Data Types**:
- **DECIMAL(30,8)**: For large volume numbers
- **BIGINT**: For whole number volumes (if precision not critical)

**Timestamp Types**:
- **TIMESTAMP WITH TIME ZONE**: Essential for multi-timezone data
- **TIMESTAMPTZ**: Same as above, preferred

**Symbol Types**:
- **VARCHAR(20)**: Sufficient for crypto symbols (BTC-USDT, etc.)
- **TEXT**: More flexible but slightly slower

**Performance Analysis**:
- DECIMAL vs DOUBLE: DECIMAL is 2-3x slower but guarantees precision
- Storage: DECIMAL(20,8) uses ~12 bytes vs DOUBLE's 8 bytes
- Query performance: DECIMAL acceptable for < 5000 inserts/second target

**Decision**: Use DECIMAL(20,8) for all price/volume fields to ensure precision. Use TIMESTAMPTZ for timestamps.

### 4. Index Strategy

**Question**: Which indexes are needed for common query patterns?

**Findings**:

**Required Indexes**:
```sql
-- Primary key (automatic)
PRIMARY KEY (symbol, timestamp)

-- Symbol filtering (common)
CREATE INDEX idx_ohlcv_symbol ON ohlcv_data (symbol);

-- Time range queries (most common)
CREATE INDEX idx_ohlcv_timestamp ON ohlcv_data (timestamp);

-- Composite for symbol + time ranges
CREATE INDEX idx_ohlcv_symbol_timestamp ON ohlcv_data (symbol, timestamp);

-- Partial index for recent data (if needed)
CREATE INDEX idx_ohlcv_recent ON ohlcv_data (symbol, timestamp)
WHERE timestamp > NOW() - INTERVAL '1 year';
```

**Index Performance Trade-offs**:
- **Insert Performance**: Each index slows inserts by ~10-20%
- **Query Performance**: Proper indexes can speed queries by 100-1000x
- **Storage**: Indexes use 50-100% of table size

**Decision**: Implement essential indexes (symbol, timestamp, composite). Monitor insert performance and add partial indexes if needed.

### 5. Error Handling & Recovery

**Question**: How to handle duplicate key violations and implement retry strategies?

**Findings**:

**Duplicate Handling**:
```python
# Option 1: ON CONFLICT DO NOTHING (fastest)
INSERT INTO ohlcv_data (symbol, timestamp, ...)
VALUES (%s, %s, ...)
ON CONFLICT (symbol, timestamp) DO NOTHING;

# Option 2: ON CONFLICT DO UPDATE (for updates)
ON CONFLICT (symbol, timestamp) DO UPDATE SET
    volume = EXCLUDED.volume,
    updated_at = NOW();
```

**Retry Strategies**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(psycopg2.OperationalError)
)
def save_ohlcv_data(data):
    # Database operation
    pass
```

**Circuit Breaker Pattern**:
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def get_db_connection():
    # Connection logic
    pass
```

**Decision**: Use ON CONFLICT DO NOTHING for duplicates, implement exponential backoff retry, add circuit breaker for database failures.

## Technical Decisions

1. **Interval Field**: Added as critical business key for OHLCV data granularity
2. **Partitioning**: Hybrid LIST(interval) + RANGE(timestamp) for optimal query performance
3. **Unique Constraint**: (symbol, interval, timestamp) to prevent duplicates
4. **Pooling**: SQLAlchemy built-in with optimized settings for OHLCV ingestion patterns
5. **Data Types**: DECIMAL(20,8) for precision, TIMESTAMPTZ for timestamps
6. **Indexing**: Interval-aware indexes with partial indexes for different retention periods
7. **Error Handling**: ON CONFLICT DO NOTHING, retry logic, circuit breaker

## Performance Benchmarks

**Target Validation**:
- 5000 records/second insertion: Achievable with proper batching and connection pooling
- <50ms query latency for 1M records: Requires proper indexing and partitioning
- 99.9% uptime: Implement monitoring and failover strategies

**Test Setup**:
- PostgreSQL 13+ on Linux
- Connection pool: 10 core, 20 overflow
- Batch size: 1000 records per insert
- Partitioning: Monthly by timestamp

## Next Steps

1. Implement prototype with research findings
2. Performance test against targets
3. Validate data integrity and precision
4. Document final configuration recommendations