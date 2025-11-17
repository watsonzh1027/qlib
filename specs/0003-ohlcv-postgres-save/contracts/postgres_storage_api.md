# PostgreSQL Storage API Contracts

**Version**: 1.0
**Date**: 2025-11-14

## Overview

This document specifies the API contracts for the PostgreSQL OHLCV storage system. All interfaces follow strict typing and error handling conventions.

## Core Interfaces

### PostgreSQLStorage Class

Main interface for OHLCV data storage and retrieval operations.

#### Constructor

```python
class PostgreSQLStorage:
    def __init__(
        self,
        connection_string: str,
        pool_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize PostgreSQL storage with connection string.

        Args:
            connection_string: PostgreSQL connection string with credentials
            pool_config: Optional connection pool configuration

        Raises:
            ConnectionError: If database connection fails
            ConfigurationError: If pool config is invalid
        """
```

#### Alternative Constructor

```python
@classmethod
def from_config(cls, config: PostgresConfig) -> 'PostgreSQLStorage':
    """
    Create storage instance from configuration object.

    Args:
        config: PostgresConfig dataclass with connection details

    Returns:
        Configured PostgreSQLStorage instance
    """

@classmethod
def from_env(cls) -> 'PostgreSQLStorage':
    """
    Create storage instance from environment variables.

    Required env vars:
    - POSTGRES_HOST
    - POSTGRES_PORT (optional, default 5432)
    - POSTGRES_DB
    - POSTGRES_USER
    - POSTGRES_PASSWORD

    Returns:
        Configured PostgreSQLStorage instance
    """
```

## Data Operations

### Save OHLCV Data

```python
def save_ohlcv_data(
    self,
    data: pd.DataFrame,
    symbol: str,
    interval: str
) -> bool:
    """
    Save OHLCV data to PostgreSQL with duplicate handling.

    Args:
        data: DataFrame with OHLCV data. Required columns:
            - timestamp: datetime64[ns, UTC]
            - open_price: float64
            - high_price: float64
            - low_price: float64
            - close_price: float64
            - volume: float64
            Optional columns:
            - quote_volume: float64
            - trade_count: Int64
            - taker_buy_volume: float64
            - taker_buy_quote_volume: float64
        symbol: Trading pair symbol (e.g., 'BTC-USDT')
        interval: Time interval ('1m', '5m', '1h', '1d', etc.)

    Returns:
        True if data saved successfully

    Raises:
        DataValidationError: If data format is invalid
        DatabaseError: If save operation fails
        DuplicateDataError: If all records are duplicates (non-critical)
    """
```

### Get OHLCV Data

```python
def get_ohlcv_data(
    self,
    symbol: str,
    interval: str,
    start_date: datetime,
    end_date: datetime
) -> pd.DataFrame:
    """
    Retrieve OHLCV data for specified symbol, interval and time range.

    Args:
        symbol: Trading pair symbol
        interval: Time interval
        start_date: Start of time range (UTC)
        end_date: End of time range (UTC)

    Returns:
        DataFrame with OHLCV data in same format as save_ohlcv_data

    Raises:
        DataNotFoundError: If no data exists for the query
        DatabaseError: If query fails
    """
```

### Get Latest Timestamp

```python
def get_latest_timestamp(
    self,
    symbol: str,
    interval: str
) -> Optional[datetime]:
    """
    Get the most recent timestamp for a symbol/interval combination.

    Args:
        symbol: Trading pair symbol
        interval: Time interval

    Returns:
        Latest timestamp or None if no data exists

    Raises:
        DatabaseError: If query fails
    """
```

### Bulk Insert

```python
def bulk_insert(self, data: List[Dict[str, Any]]) -> int:
    """
    Perform high-performance bulk insert of OHLCV records.

    Args:
        data: List of dictionaries with OHLCV data. Each dict must contain:
            - symbol: str
            - interval: str
            - timestamp: datetime
            - open_price: float
            - high_price: float
            - low_price: float
            - close_price: float
            - volume: float
            Plus optional fields as in save_ohlcv_data

    Returns:
        Number of records successfully inserted (duplicates not counted)

    Raises:
        DataValidationError: If data format is invalid
        DatabaseError: If bulk insert fails
    """
```

### Get Available Intervals

```python
def get_available_intervals(self, symbol: str) -> List[str]:
    """
    Get all available intervals for a symbol.

    Args:
        symbol: Trading pair symbol

    Returns:
        List of available intervals, sorted by granularity

    Raises:
        DatabaseError: If query fails
    """
```

## Health and Monitoring

### Health Check

```python
def health_check(self) -> bool:
    """
    Perform comprehensive health check of database connection and schema.

    Checks:
    - Database connectivity
    - Required tables exist
    - Recent partitions exist
    - Basic query performance

    Returns:
        True if all checks pass

    Raises:
        HealthCheckError: If any check fails (with details)
    """
```

### Connection Pool Stats

```python
def get_pool_stats(self) -> Dict[str, Any]:
    """
    Get current connection pool statistics.

    Returns:
        Dict with pool metrics:
        - pool_size: int
        - checked_out: int
        - overflow: int
        - invalid: int

    Raises:
        DatabaseError: If stats cannot be retrieved
    """
```

## Configuration Schema

### PostgresConfig Dataclass

```python
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class PostgresConfig:
    """Configuration for PostgreSQL OHLCV storage."""

    # Connection settings
    host: str
    port: int = 5432
    database: str
    user: str
    password: str

    # Connection pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600  # Recycle connections after 1 hour
    pool_pre_ping: bool = True  # Check connection health

    # Business logic settings
    supported_intervals: List[str] = field(default_factory=lambda: [
        '1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'
    ])

    retention_days: Dict[str, int] = field(default_factory=lambda: {
        '1m': 365,    # 1 year
        '5m': 365,    # 1 year
        '15m': 730,   # 2 years
        '1h': 730,    # 2 years
        '4h': 1095,   # 3 years
        '1d': -1      # indefinite
    })

    # Performance tuning
    batch_size: int = 1000  # Records per batch insert
    max_query_limit: int = 100000  # Max records per query

    def get_connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.pool_size < 1:
            raise ValueError("pool_size must be >= 1")
        if self.max_overflow < 0:
            raise ValueError("max_overflow must be >= 0")
        if not all(interval in self.supported_intervals for interval in self.retention_days.keys()):
            raise ValueError("retention_days keys must be subset of supported_intervals")
```

## Error Handling

### Exception Hierarchy

```python
class PostgresStorageError(Exception):
    """Base exception for PostgreSQL storage operations."""
    pass

class ConnectionError(PostgresStorageError):
    """Database connection failures."""
    pass

class DataValidationError(PostgresStorageError):
    """Data format or validation errors."""
    pass

class DatabaseError(PostgresStorageError):
    """General database operation errors."""
    pass

class DuplicateDataError(PostgresStorageError):
    """Non-critical error for duplicate data (handled gracefully)."""
    pass

class DataNotFoundError(PostgresStorageError):
    """No data found for query."""
    pass

class HealthCheckError(PostgresStorageError):
    """Health check failures."""
    pass

class ConfigurationError(PostgresStorageError):
    """Configuration validation errors."""
    pass
```

### Error Response Format

All exceptions include:
- `message`: Human-readable error description
- `error_code`: Machine-readable error code
- `context`: Additional error context (optional)

Example:
```python
try:
    storage.save_ohlcv_data(data, 'BTC-USDT', '1h')
except DataValidationError as e:
    print(f"Validation failed: {e.message}")
    print(f"Error code: {e.error_code}")
    if hasattr(e, 'context'):
        print(f"Context: {e.context}")
```

## Data Formats

### OHLCV Record Schema

```python
OHLCVRecord = TypedDict('OHLCVRecord', {
    'symbol': str,
    'interval': str,
    'timestamp': datetime,
    'open_price': float,
    'high_price': float,
    'low_price': float,
    'close_price': float,
    'volume': float,
    'quote_volume': Optional[float],
    'trade_count': Optional[int],
    'taker_buy_volume': Optional[float],
    'taker_buy_quote_volume': Optional[float]
}, total=False)
```

### Query Result Format

Query methods return pandas DataFrames with:
- Consistent column naming
- Proper dtypes (datetime64[ns, UTC] for timestamps)
- Sorted by timestamp ascending
- No duplicate records

## Performance Contracts

### Latency Guarantees

- `save_ohlcv_data`: < 100ms for batches up to 1000 records
- `get_ohlcv_data`: < 50ms for queries returning up to 10,000 records
- `get_latest_timestamp`: < 10ms
- `bulk_insert`: < 200ms for batches up to 5000 records

### Throughput Guarantees

- Sustained ingestion: ≥ 5000 records/second
- Query throughput: ≥ 100 queries/second
- Connection pool efficiency: ≥ 90% utilization without queuing

### Data Consistency

- **Atomicity**: All operations are atomic (single record or complete batch)
- **Isolation**: Read committed isolation level
- **Durability**: Data durability guaranteed after successful commit

## Version Compatibility

### API Versioning

- **v1.0**: Initial release with core OHLCV operations
- **Backward Compatibility**: All v1.0 clients remain compatible
- **Deprecation Policy**: 6 months notice for breaking changes

### Data Schema Evolution

- **Additive Changes**: New optional fields can be added without breaking changes
- **Migration Support**: Automatic schema migration for non-breaking changes
- **Breaking Changes**: Require explicit migration scripts and version updates

## Testing Contracts

### Unit Test Requirements

All methods must have unit tests covering:
- Happy path scenarios
- Error conditions
- Edge cases (empty data, invalid formats)
- Performance assertions

### Integration Test Requirements

End-to-end tests must validate:
- Full data pipeline from save to query
- Database connection resilience
- Data integrity across operations
- Performance under load

### Test Data Standards

- Use realistic OHLCV data for testing
- Include multiple symbols and intervals
- Test with various batch sizes
- Validate against known performance baselines