"""
PostgreSQL Storage for OHLCV Data

This module provides PostgreSQL-based storage for OHLCV cryptocurrency data
with optimized partitioning, indexing, and performance for time-series queries.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import create_engine, Column, String, DateTime, Numeric, Integer, text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

# Configure logging
logger = logging.getLogger(__name__)

# SQLAlchemy base
Base = declarative_base()

# OHLCV Data Model
class OHLCVData(Base):
    """SQLAlchemy model for OHLCV data."""
    __tablename__ = 'ohlcv_data'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    interval = Column(String(10), nullable=False)
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
    funding_rate = Column(Numeric(20, 10))  # Added
    vwap = Column(Numeric(20, 8))           # Added
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('symbol', 'interval', 'timestamp', name='unique_symbol_interval_timestamp'),
        # Removed schema specification to use default public schema
    )


# Funding Rate Data Model
class FundingRateData(Base):
    """SQLAlchemy model for funding rate data."""
    __tablename__ = 'funding_rates'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    funding_rate = Column(Numeric(20, 10), nullable=False)  # Higher precision for funding rates
    next_funding_time = Column(DateTime(timezone=True))
    mark_price = Column(Numeric(20, 8))
    index_price = Column(Numeric(20, 8))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('symbol', 'timestamp', name='unique_funding_symbol_timestamp'),
        # Removed schema specification to use default public schema
    )


# Configuration
@dataclass
class PostgresConfig:
    """Configuration for PostgreSQL OHLCV storage."""

    # Connection settings
    host: str
    database: str
    user: str
    password: str
    port: int = 5432
    ssl_mode: str = "require"

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
            f"?sslmode={self.ssl_mode}"
        )

    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.pool_size < 1:
            raise ValueError("pool_size must be >= 1")
        if self.max_overflow < 0:
            raise ValueError("max_overflow must be >= 0")
        if not all(interval in self.supported_intervals for interval in self.retention_days.keys()):
            raise ValueError("retention_days keys must be subset of supported_intervals")

# Custom Exceptions
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

# Main Storage Class
class PostgreSQLStorage:
    """
    PostgreSQL storage implementation for OHLCV data.

    Features:
    - Hybrid LIST(interval) + RANGE(timestamp) partitioning
    - Optimized indexing for time-series queries
    - Connection pooling with health checks
    - Comprehensive error handling and validation
    """

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
        try:
            # Default pool configuration
            default_pool_config = {
                'poolclass': QueuePool,
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'pool_pre_ping': True,
                'echo': False  # Set to True for SQL debugging
            }

            # Override with custom config
            if pool_config:
                default_pool_config.update(pool_config)

            # Create engine
            self.engine = create_engine(
                connection_string,
                **default_pool_config
            )

            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            # Create tables if they don't exist
            Base.metadata.create_all(bind=self.engine)

            logger.info("PostgreSQL storage initialized successfully")

        except OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            raise ConnectionError(f"Failed to connect to database: {e}") from e
        except Exception as e:
            logger.error(f"Storage initialization failed: {e}")
            raise ConfigurationError(f"Invalid configuration: {e}") from e

    @classmethod
    def from_config(cls, config: PostgresConfig) -> 'PostgreSQLStorage':
        """
        Create storage instance from configuration object.

        Args:
            config: PostgresConfig dataclass with connection details

        Returns:
            Configured PostgreSQLStorage instance
        """
        config.validate()
        pool_config = {
            'pool_size': config.pool_size,
            'max_overflow': config.max_overflow,
            'pool_timeout': config.pool_timeout,
            'pool_recycle': config.pool_recycle,
            'pool_pre_ping': config.pool_pre_ping
        }
        return cls(config.get_connection_string(), pool_config)

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
        - POSTGRES_SSL_MODE (optional, default 'require')

        Returns:
            Configured PostgreSQLStorage instance
        """
        config = PostgresConfig(
            host=os.getenv('POSTGRES_HOST'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            ssl_mode=os.getenv('POSTGRES_SSL_MODE', 'require')
        )

        missing = []
        if not config.host: missing.append('POSTGRES_HOST')
        if not config.database: missing.append('POSTGRES_DB')
        if not config.user: missing.append('POSTGRES_USER')
        if not config.password: missing.append('POSTGRES_PASSWORD')

        if missing:
            raise ConfigurationError(f"Missing required environment variables: {missing}")

        return cls.from_config(config)

    def _get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    def _validate_ohlcv_data(self, data: pd.DataFrame) -> None:
        """
        Validate OHLCV DataFrame format and content.

        Args:
            data: DataFrame to validate

        Raises:
            DataValidationError: If validation fails
        """
        errors = []

        # Required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")

        if errors:
            raise DataValidationError(f"Data validation failed: {'; '.join(errors)}")

        # Data type checks
        if not pd.api.types.is_datetime64tz_dtype(data['timestamp']):
            errors.append("timestamp column must be timezone-aware datetime")

        # Value checks (sample first 100 rows)
        sample = data.head(100)
        if (sample['volume'] < 0).any():
            errors.append("Volume must be non-negative")

        if (sample[['open', 'high', 'low', 'close']] <= 0).any().any():
            errors.append("Prices must be positive")

        # OHLC relationships
        invalid_ohlc = (
            (sample['high'] < sample['open']) |
            (sample['high'] < sample['close']) |
            (sample['low'] > sample['open']) |
            (sample['low'] > sample['close'])
        )
        if invalid_ohlc.any():
            errors.append("Invalid OHLC relationships")

        if errors:
            raise DataValidationError(f"Data validation failed: {'; '.join(errors)}")

    def save_ohlcv_data(
        self,
        data: pd.DataFrame,
        symbol: str,
        interval: str
    ) -> bool:
        """
        Save OHLCV data to PostgreSQL with duplicate handling.

        Args:
            data: DataFrame with OHLCV data
            symbol: Trading pair symbol (e.g., 'BTC-USDT')
            interval: Time interval ('1m', '5m', '1h', '1d', etc.)

        Returns:
            True if data saved successfully

        Raises:
            DataValidationError: If data format is invalid
            DatabaseError: If save operation fails
        """
        try:
            # Validate input
            if data.empty:
                logger.warning("Empty data provided, skipping save")
                return True

            self._validate_ohlcv_data(data)

            # Prepare data for insertion
            records = []
            for _, row in data.iterrows():
                # Ensure timestamp is a proper Python datetime with UTC timezone
                timestamp = row['timestamp']
                if isinstance(timestamp, pd.Timestamp):
                    # Convert pandas Timestamp to Python datetime
                    timestamp = timestamp.to_pydatetime()
                elif not isinstance(timestamp, datetime):
                    # If it's not already a datetime, try to convert
                    timestamp = pd.to_datetime(timestamp, utc=True).to_pydatetime()
                
                # Ensure it's UTC timezone-aware
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                else:
                    timestamp = timestamp.astimezone(timezone.utc)
                
                record = {
                    'symbol': symbol,
                    'interval': interval,
                    'timestamp': timestamp,
                    'open_price': row['open'],
                    'high_price': row['high'],
                    'low_price': row['low'],
                    'close_price': row['close'],
                    'volume': row['volume'],
                    'quote_volume': row.get('quote_volume'),
                    'trade_count': row.get('trade_count'),
                    'taker_buy_volume': row.get('taker_buy_volume'),
                    'taker_buy_volume': row.get('taker_buy_volume'),
                    'taker_buy_quote_volume': row.get('taker_buy_quote_volume'),
                    'funding_rate': row.get('funding_rate'),
                    'vwap': row.get('vwap')
                }
                records.append(record)

            # Bulk insert with ON CONFLICT DO NOTHING
            with self._get_session() as session:
                # Use raw SQL for better performance with ON CONFLICT
                insert_sql = text("""
                    INSERT INTO ohlcv_data (
                        symbol, interval, timestamp, open_price, high_price,
                        low_price, close_price, volume, quote_volume,
                        trade_count, taker_buy_volume, taker_buy_quote_volume,
                        funding_rate, vwap
                    ) VALUES (
                        :symbol, :interval, :timestamp, :open_price, :high_price,
                        :low_price, :close_price, :volume, :quote_volume,
                        :trade_count, :taker_buy_volume, :taker_buy_quote_volume,
                        :funding_rate, :vwap
                    )
                    ON CONFLICT (symbol, interval, timestamp) DO NOTHING
                """)

                # Insert in batches
                batch_size = 1000
                inserted_count = 0

                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    try:
                        session.execute(insert_sql, batch)
                        session.commit()
                        inserted_count += len(batch)
                    except SQLAlchemyError as e:
                        # Rollback the failed batch before trying individual inserts
                        session.rollback()
                        logger.warning(f"Batch insert failed ({e}), trying individual inserts...")
                        for record in batch:
                            try:
                                session.execute(insert_sql, [record])
                                session.commit()
                                inserted_count += 1
                            except SQLAlchemyError:
                                # Duplicate or other error for this single record, skip
                                session.rollback()
                                pass

                logger.info(f"Successfully saved {inserted_count} OHLCV records for {symbol} {interval}")
                return True

        except DataValidationError:
            raise  # Re-raise validation errors
        except IntegrityError as e:
            logger.warning(f"Data integrity issue: {e}")
            raise DuplicateDataError("Duplicate data detected") from e
        except SQLAlchemyError as e:
            logger.error(f"Database error during save: {e}")
            raise DatabaseError(f"Failed to save OHLCV data: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during save: {e}")
            raise DatabaseError(f"Unexpected error: {e}") from e

    def get_ohlcv_data(
        self,
        symbol: str,
        interval: str,
        start_date: datetime = None,
        end_date: datetime = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> pd.DataFrame:
        """
        Retrieve OHLCV data for specified symbol, interval and time range.

        NOTE: Accepts either `start_date`/`end_date` or `start_time`/`end_time` for compatibility with callers.

        Args:
            symbol: Trading pair symbol
            interval: Time interval
            start_date/start_time: Start of time range (UTC)
            end_date/end_time: End of time range (UTC)

        Returns:
            DataFrame with OHLCV data

        Raises:
            DataNotFoundError: If no data exists for the query
            DatabaseError: If query fails
        """
        # Normalize parameter aliases
        if start_date is None and start_time is not None:
            start_date = start_time
        if end_date is None and end_time is not None:
            end_date = end_time

        if start_date is None or end_date is None:
            raise ValueError("Both start and end times must be provided (start_date/start_time, end_date/end_time)")
        try:
            query = text("""
                SELECT
                    symbol, interval, timestamp, open_price, high_price,
                    low_price, close_price, volume, quote_volume,
                    trade_count, taker_buy_volume, taker_buy_quote_volume,
                    funding_rate, vwap,
                    created_at, updated_at
                FROM ohlcv_data
                WHERE symbol = :symbol
                  AND interval = :interval
                  AND timestamp >= :start_date
                  AND timestamp <= :end_date
                ORDER BY timestamp ASC
                LIMIT :max_limit
            """)

            with self.engine.connect() as conn:
                result = conn.execute(query, {
                    'symbol': symbol,
                    'interval': interval,
                    'start_date': start_date,
                    'end_date': end_date,
                    'max_limit': 100000  # Prevent excessive memory usage
                })

                rows = result.fetchall()

            if not rows:
                raise DataNotFoundError(
                    f"No data found for {symbol} {interval} between {start_date} and {end_date}"
                )

            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=[
                'symbol', 'interval', 'timestamp', 'open_price', 'high_price',
                'low_price', 'close_price', 'volume', 'quote_volume',
                'trade_count', 'taker_buy_volume', 'taker_buy_quote_volume',
                'funding_rate', 'vwap',
                'created_at', 'updated_at'
            ])

            # Ensure proper dtypes
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
            df['updated_at'] = pd.to_datetime(df['updated_at'], utc=True)

            logger.info(f"Retrieved {len(df)} OHLCV records for {symbol} {interval}")
            return df

        except DataNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error during query: {e}")
            raise DatabaseError(f"Failed to query OHLCV data: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during query: {e}")
            raise DatabaseError(f"Unexpected error: {e}") from e

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
        """
        try:
            query = text("""
                SELECT timestamp
                FROM ohlcv_data
                WHERE symbol = :symbol AND interval = :interval
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            with self.engine.connect() as conn:
                result = conn.execute(query, {'symbol': symbol, 'interval': interval})
                row = result.fetchone()

            return row[0] if row else None

        except SQLAlchemyError as e:
            logger.error(f"Database error getting latest timestamp: {e}")
            raise DatabaseError(f"Failed to get latest timestamp: {e}") from e

    def bulk_insert(self, data: List[Dict[str, Any]]) -> int:
        """
        Perform high-performance bulk insert of OHLCV records.

        Args:
            data: List of dictionaries with OHLCV data

        Returns:
            Number of records successfully inserted
        """
        if not data:
            return 0

        try:
            # Use save_ohlcv_data for now (can be optimized later)
            # Convert list of dicts to DataFrame
            df = pd.DataFrame(data)

            # Extract symbol and interval from first record
            symbol = data[0]['symbol']
            interval = data[0]['interval']

            # Validate all records have same symbol/interval
            for record in data[1:]:
                if record['symbol'] != symbol or record['interval'] != interval:
                    raise DataValidationError("All records must have same symbol and interval")

            # Convert timestamp strings if needed
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

            self.save_ohlcv_data(df, symbol, interval)
            return len(data)

        except (DataValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error during bulk insert: {e}")
            raise DatabaseError(f"Bulk insert failed: {e}") from e

    def get_available_intervals(self, symbol: str) -> List[str]:
        """
        Get all available intervals for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            List of available intervals, sorted by granularity
        """
        try:
            query = text("""
                SELECT DISTINCT interval
                FROM ohlcv_data
                WHERE symbol = :symbol
                ORDER BY
                    CASE
                        WHEN interval LIKE '%m' THEN 1
                        WHEN interval LIKE '%h' THEN 2
                        WHEN interval LIKE '%d' THEN 3
                        WHEN interval LIKE '%w' THEN 4
                        WHEN interval LIKE '%M' THEN 5
                        ELSE 6
                    END,
                    CAST(SUBSTRING(interval FROM 1 FOR LENGTH(interval) - 1) AS INTEGER)
            """)

            with self.engine.connect() as conn:
                result = conn.execute(query, {'symbol': symbol})
                rows = result.fetchall()

            return [row[0] for row in rows]

        except SQLAlchemyError as e:
            logger.error(f"Database error getting available intervals: {e}")
            raise DatabaseError(f"Failed to get available intervals: {e}") from e

    def health_check(self) -> bool:
        """
        Perform comprehensive health check of database connection and schema.

        Returns:
            True if all checks pass

        Raises:
            HealthCheckError: If any check fails
        """
        checks = []

        try:
            # Connection check
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks.append(("connection", True, "OK"))

            # Table existence check
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'ohlcv_data'
                    )
                """))
                table_exists = result.fetchone()[0]

            if table_exists:
                checks.append(("table_exists", True, "OK"))
            else:
                checks.append(("table_exists", False, "Table ohlcv_data not found"))

            # Recent data check (data from last 24 hours) - optional for empty databases
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM ohlcv_data
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                """))
                recent_count = result.fetchone()[0]

            # For health check, recent data is optional (database might be empty)
            checks.append(("recent_data", True, f"{recent_count} records in last 24h"))

            # All checks passed?
            all_passed = all(check[1] for check in checks)

            if not all_passed:
                failed_checks = [check[0] for check in checks if not check[1]]
                raise HealthCheckError(f"Health check failed: {failed_checks}")

            logger.info("Health check passed")
            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HealthCheckError(f"Health check failed: {e}") from e

    def get_pool_stats(self) -> Dict[str, Any]:
        """
        Get current connection pool statistics.

        Returns:
            Dict with pool metrics
        """
        try:
            pool = self.engine.pool
            return {
                'pool_size': getattr(pool, 'size', 0),
                'checked_out': getattr(pool, 'checked_out', 0),
                'overflow': getattr(pool, 'overflow', 0),
                'invalid': getattr(pool, 'invalid', 0),
                'checkedin': getattr(pool, '_checkedin', 0),
                'total': getattr(pool, '_total', 0)
            }
        except Exception as e:
            logger.error(f"Failed to get pool stats: {e}")
            return {}
    
    def save_funding_rates(
        self,
        data: pd.DataFrame,
        symbol: str
    ) -> bool:
        """
        Save funding rate data to PostgreSQL with duplicate handling.

        Args:
            data: DataFrame with funding rate data
            symbol: Trading pair symbol (e.g., 'BTC-USDT')

        Returns:
            True if data saved successfully

        Raises:
            DataValidationError: If data format is invalid
            DatabaseError: If save operation fails
        """
        try:
            # Validate input
            if data.empty:
                logger.warning("Empty funding rate data provided, skipping save")
                return True

            # Required columns for funding rates
            required_cols = ['timestamp', 'funding_rate']
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                raise DataValidationError(f"Missing required columns: {missing_cols}")

            # Prepare data for insertion
            records = []
            for _, row in data.iterrows():
                # Ensure timestamp is a proper Python datetime with UTC timezone
                timestamp = row['timestamp']
                if isinstance(timestamp, pd.Timestamp):
                    timestamp = timestamp.to_pydatetime()
                elif not isinstance(timestamp, datetime):
                    timestamp = pd.to_datetime(timestamp, utc=True).to_pydatetime()
                
                # Ensure it's UTC timezone-aware
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                else:
                    timestamp = timestamp.astimezone(timezone.utc)
                
                # Handle next_funding_time if present
                next_funding_time = row.get('next_funding_time')
                if next_funding_time and not pd.isna(next_funding_time):
                    if isinstance(next_funding_time, pd.Timestamp):
                        next_funding_time = next_funding_time.to_pydatetime()
                    elif not isinstance(next_funding_time, datetime):
                        next_funding_time = pd.to_datetime(next_funding_time, utc=True).to_pydatetime()
                    
                    if next_funding_time.tzinfo is None:
                        next_funding_time = next_funding_time.replace(tzinfo=timezone.utc)
                    else:
                        next_funding_time = next_funding_time.astimezone(timezone.utc)
                else:
                    next_funding_time = None
                
                record = {
                    'symbol': symbol,
                    'timestamp': timestamp,
                    'funding_rate': row['funding_rate'],
                    'next_funding_time': next_funding_time,
                    'mark_price': row.get('mark_price'),
                    'index_price': row.get('index_price')
                }
                records.append(record)

            # Bulk insert with ON CONFLICT DO UPDATE (update if newer data)
            with self._get_session() as session:
                insert_sql = text("""
                    INSERT INTO funding_rates (
                        symbol, timestamp, funding_rate, next_funding_time,
                        mark_price, index_price
                    ) VALUES (
                        :symbol, :timestamp, :funding_rate, :next_funding_time,
                        :mark_price, :index_price
                    )
                    ON CONFLICT (symbol, timestamp) DO UPDATE SET
                        funding_rate = EXCLUDED.funding_rate,
                        next_funding_time = EXCLUDED.next_funding_time,
                        mark_price = EXCLUDED.mark_price,
                        index_price = EXCLUDED.index_price,
                        updated_at = NOW()
                """)

                # Insert in batches
                batch_size = 1000
                inserted_count = 0

                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    try:
                        session.execute(insert_sql, batch)
                        session.commit()
                        inserted_count += len(batch)
                    except SQLAlchemyError as e:
                        session.rollback()
                        logger.warning(f"Batch insert failed ({e}), trying individual inserts...")
                        for record in batch:
                            try:
                                session.execute(insert_sql, [record])
                                session.commit()
                                inserted_count += 1
                            except SQLAlchemyError:
                                session.rollback()
                                pass

                logger.info(f"Successfully saved {inserted_count} funding rate records for {symbol}")
                return True

        except DataValidationError:
            raise
        except IntegrityError as e:
            logger.warning(f"Data integrity issue: {e}")
            raise DuplicateDataError("Duplicate funding rate data detected") from e
        except SQLAlchemyError as e:
            logger.error(f"Database error during save: {e}")
            raise DatabaseError(f"Failed to save funding rate data: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during save: {e}")
            raise DatabaseError(f"Unexpected error: {e}") from e
    
    def get_funding_rates(
        self,
        symbol: str,
        start_date: datetime = None,
        end_date: datetime = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> pd.DataFrame:
        """
        Retrieve funding rate data for specified symbol and time range.

        NOTE: This method accepts both `start_date`/`end_date` and `start_time`/`end_time`
        as argument names for backward compatibility with different callers.

        Args:
            symbol: Trading pair symbol
            start_date / start_time: Start of time range (UTC)
            end_date / end_time: End of time range (UTC)

        Returns:
            DataFrame with funding rate data

        Raises:
            DataNotFoundError: If no data exists for the query
            DatabaseError: If query fails
        """
        # Accept either naming convention
        if start_date is None and start_time is not None:
            start_date = start_time
        if end_date is None and end_time is not None:
            end_date = end_time

        if start_date is None or end_date is None:
            raise ValueError("Both start and end times must be provided (start_date/start_time, end_date/end_time)")

        try:
            # funding_rates table may not contain `created_at` in all schema versions.
            # Select only columns we are certain exist (updated_at is used by upsert),
            # and build DataFrame accordingly.
            query = text("""
                SELECT
                    symbol, timestamp, funding_rate, next_funding_time,
                    mark_price, index_price, updated_at
                FROM funding_rates
                WHERE symbol = :symbol
                  AND timestamp >= :start_date
                  AND timestamp <= :end_date
                ORDER BY timestamp ASC
                LIMIT :max_limit
            """)

            with self.engine.connect() as conn:
                result = conn.execute(query, {
                    'symbol': symbol,
                    'start_date': start_date,
                    'end_date': end_date,
                    'max_limit': 100000
                })

                rows = result.fetchall()

            if not rows:
                raise DataNotFoundError(
                    f"No funding rate data found for {symbol} between {start_date} and {end_date}"
                )

            # Convert to DataFrame; note `created_at` may be absent so we only include `updated_at`
            df = pd.DataFrame(rows, columns=[
                'symbol', 'timestamp', 'funding_rate', 'next_funding_time',
                'mark_price', 'index_price', 'updated_at'
            ])

            # Ensure proper dtypes
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            if 'next_funding_time' in df.columns:
                df['next_funding_time'] = pd.to_datetime(df['next_funding_time'], utc=True)
            df['updated_at'] = pd.to_datetime(df['updated_at'], utc=True)

            # For compatibility, provide a `created_at` column by copying `updated_at` if needed
            if 'created_at' not in df.columns:
                df['created_at'] = df['updated_at']

            logger.info(f"Retrieved {len(df)} funding rate records for {symbol}")
            return df

        except DataNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error during query: {e}")
            raise DatabaseError(f"Failed to query funding rate data: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during query: {e}")
            raise DatabaseError(f"Unexpected error: {e}") from e
    
    def get_latest_funding_rate_timestamp(
        self,
        symbol: str
    ) -> Optional[datetime]:
        """
        Get the most recent funding rate timestamp for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Latest timestamp or None if no data exists
        """
        try:
            query = text("""
                SELECT timestamp
                FROM funding_rates
                WHERE symbol = :symbol
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            with self.engine.connect() as conn:
                result = conn.execute(query, {'symbol': symbol})
                row = result.fetchone()

            return row[0] if row else None

        except SQLAlchemyError as e:
            logger.error(f"Database error getting latest funding rate timestamp: {e}")
            raise DatabaseError(f"Failed to get latest funding rate timestamp: {e}") from e