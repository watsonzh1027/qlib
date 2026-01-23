"""
PostgreSQL Configuration Management

This module provides configuration management for PostgreSQL OHLCV storage,
including environment variable handling, validation, and schema setup utilities.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

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

    # Schema settings
    schema_name: str = "public"  # PostgreSQL schema to use
    create_schema_if_not_exists: bool = True

    def get_connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    def validate(self) -> None:
        """Validate configuration parameters."""
        errors = []

        # Connection validation
        if not self.host or not self.host.strip():
            errors.append("host is required")
        if not self.database or not self.database.strip():
            errors.append("database is required")
        if not self.user or not self.user.strip():
            errors.append("user is required")
        if not self.password:
            errors.append("password is required")

        # Port validation
        if not (1024 <= self.port <= 65535):
            errors.append("port must be between 1024 and 65535")

        # Pool settings validation
        if self.pool_size < 1:
            errors.append("pool_size must be >= 1")
        if self.max_overflow < 0:
            errors.append("max_overflow must be >= 0")
        if self.pool_timeout < 1:
            errors.append("pool_timeout must be >= 1")
        if self.pool_recycle < 60:
            errors.append("pool_recycle must be >= 60 seconds")

        # Business logic validation
        if not self.supported_intervals:
            errors.append("supported_intervals cannot be empty")
        if not all(interval in self.supported_intervals for interval in self.retention_days.keys()):
            errors.append("retention_days keys must be subset of supported_intervals")

        # Retention validation
        for interval, days in self.retention_days.items():
            if days != -1 and days < 1:
                errors.append(f"retention_days[{interval}] must be -1 (indefinite) or >= 1")

        # Performance validation
        if self.batch_size < 1:
            errors.append("batch_size must be >= 1")
        if self.max_query_limit < 1000:
            errors.append("max_query_limit must be >= 1000")

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

    @classmethod
    def from_env(cls) -> 'PostgresConfig':
        """
        Create configuration from environment variables.

        Required env vars:
        - POSTGRES_HOST
        - POSTGRES_DB
        - POSTGRES_USER
        - POSTGRES_PASSWORD

        Optional env vars:
        - POSTGRES_PORT (default: 5432)
        - POSTGRES_POOL_SIZE (default: 10)
        - POSTGRES_MAX_OVERFLOW (default: 20)
        - POSTGRES_POOL_TIMEOUT (default: 30)
        - POSTGRES_SCHEMA (default: public)
        """
        # Get required values
        host = os.getenv('POSTGRES_HOST')
        database = os.getenv('POSTGRES_DB')
        user = os.getenv('POSTGRES_USER')
        password = os.getenv('POSTGRES_PASSWORD')

        # Check required values
        missing = []
        if not host: missing.append('POSTGRES_HOST')
        if not database: missing.append('POSTGRES_DB')
        if not user: missing.append('POSTGRES_USER')
        if not password: missing.append('POSTGRES_PASSWORD')

        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")

        # Get optional values with defaults
        config = cls(
            host=host,
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=database,
            user=user,
            password=password,
            pool_size=int(os.getenv('POSTGRES_POOL_SIZE', 10)),
            max_overflow=int(os.getenv('POSTGRES_MAX_OVERFLOW', 20)),
            pool_timeout=int(os.getenv('POSTGRES_POOL_TIMEOUT', 30)),
            schema_name=os.getenv('POSTGRES_SCHEMA', 'public')
        )

        return config

    @classmethod
    def from_file(cls, config_path: str) -> 'PostgresConfig':
        """
        Load configuration from JSON file.

        Args:
            config_path: Path to JSON configuration file

        Returns:
            PostgresConfig instance
        """
        import json

        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(path, 'r') as f:
            data = json.load(f)

        # Extract nested config if present
        config_data = data.get('postgres', data.get('database', data))

        # Handle retention_days conversion (JSON doesn't support int keys)
        retention_days = {}
        if 'retention_days' in config_data:
            for k, v in config_data['retention_days'].items():
                retention_days[k] = v

        config = cls(
            host=config_data['host'],
            port=config_data.get('port', 5432),
            database=config_data['database'],
            user=config_data['user'],
            password=config_data['password'],
            pool_size=config_data.get('pool_size', 10),
            max_overflow=config_data.get('max_overflow', 20),
            pool_timeout=config_data.get('pool_timeout', 30),
            pool_recycle=config_data.get('pool_recycle', 3600),
            pool_pre_ping=config_data.get('pool_pre_ping', True),
            supported_intervals=config_data.get('supported_intervals', [
                '1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'
            ]),
            retention_days=retention_days or {
                '1m': 365, '5m': 365, '15m': 730, '1h': 730, '4h': 1095, '1d': -1
            },
            batch_size=config_data.get('batch_size', 1000),
            max_query_limit=config_data.get('max_query_limit', 100000),
            schema_name=config_data.get('schema_name', 'public')
        )

        return config

    def to_file(self, config_path: str) -> None:
        """
        Save configuration to JSON file.

        Args:
            config_path: Path to save configuration file
        """
        import json

        config_dict = {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
            'pool_recycle': self.pool_recycle,
            'pool_pre_ping': self.pool_pre_ping,
            'supported_intervals': self.supported_intervals,
            'retention_days': self.retention_days,
            'batch_size': self.batch_size,
            'max_query_limit': self.max_query_limit,
            'schema_name': self.schema_name,
            'create_schema_if_not_exists': self.create_schema_if_not_exists
        }

        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(config_dict, f, indent=2)

        logger.info(f"Configuration saved to {config_path}")

    def get_connection_dict(self) -> Dict[str, Any]:
        """
        Get connection parameters as dictionary.

        Returns:
            Dictionary suitable for database connection
        """
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'ssl_mode': self.ssl_mode
        }

class PostgresConfigManager:
    """
    Configuration manager for PostgreSQL settings.

    Provides utilities for loading, validating, and managing
    PostgreSQL configurations across different environments.
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_dir: Directory to search for configuration files
        """
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self, name: str = 'default') -> PostgresConfig:
        """
        Load configuration by name.

        Search order:
        1. Environment variables (if name == 'env')
        2. JSON file: {config_dir}/{name}.json
        3. JSON file: {config_dir}/postgres.json

        Args:
            name: Configuration name

        Returns:
            Loaded and validated PostgresConfig
        """
        if name == 'env':
            config = PostgresConfig.from_env()
        else:
            # Try named config file
            config_path = self.config_dir / f'{name}.json'
            if not config_path.exists():
                # Try default postgres.json
                config_path = self.config_dir / 'postgres.json'
                if not config_path.exists():
                    raise FileNotFoundError(
                        f"Configuration file not found: {config_path} or {self.config_dir / f'{name}.json'}"
                    )

            config = PostgresConfig.from_file(str(config_path))

        config.validate()
        logger.info(f"Loaded configuration: {name}")
        return config

    def save_config(self, config: PostgresConfig, name: str = 'default') -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration to save
            name: Configuration name
        """
        config.validate()
        config_path = self.config_dir / f'{name}.json'
        config.to_file(str(config_path))
        logger.info(f"Saved configuration: {name}")

    def list_configs(self) -> List[str]:
        """
        List available configuration files.

        Returns:
            List of configuration names
        """
        configs = []
        if self.config_dir.exists():
            for config_file in self.config_dir.glob('*.json'):
                if config_file.name != 'postgres.json':
                    configs.append(config_file.stem)
            if (self.config_dir / 'postgres.json').exists():
                configs.append('default')

        return sorted(configs)

    def create_default_config(self, **overrides) -> PostgresConfig:
        """
        Create a default configuration with optional overrides.

        Args:
            **overrides: Configuration overrides

        Returns:
            Default PostgresConfig with overrides applied
        """
        defaults = {
            'host': 'localhost',
            'database': 'qlib_crypto',
            'user': 'crypto_user',
            'password': 'change_me_in_production',
            'ssl_mode': 'require'
        }

        defaults.update(overrides)
        config = PostgresConfig(**defaults)
        config.validate()
        return config

# Utility functions
def setup_database_schema(config: PostgresConfig, drop_existing: bool = False) -> None:
    """
    Set up database schema and initial partitions.

    Args:
        config: Database configuration
        drop_existing: Whether to drop existing schema
    """
    from sqlalchemy import create_engine, text

    engine = create_engine(config.get_connection_string())

    try:
        with engine.connect() as conn:
            # Create schema if needed
            if config.schema_name != 'public':
                if config.create_schema_if_not_exists:
                    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {config.schema_name}"))
                    logger.info(f"Created schema: {config.schema_name}")

                conn.execute(text(f"SET search_path TO {config.schema_name}"))

            # Drop existing table if requested
            if drop_existing:
                conn.execute(text("DROP TABLE IF EXISTS ohlcv_data CASCADE"))
                logger.info("Dropped existing ohlcv_data table")

            # Create main table with partitioning
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS ohlcv_data (
                symbol VARCHAR(20) NOT NULL,
                interval VARCHAR(10) NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                open_price DECIMAL(20,8) NOT NULL,
                high_price DECIMAL(20,8) NOT NULL,
                low_price DECIMAL(20,8) NOT NULL,
                close_price DECIMAL(20,8) NOT NULL,
                volume DECIMAL(20,8) NOT NULL,
                quote_volume DECIMAL(20,8),
                trade_count INTEGER,
                taker_buy_volume DECIMAL(20,8),
                taker_buy_quote_volume DECIMAL(20,8),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                PRIMARY KEY (symbol, interval, timestamp)
            ) PARTITION BY LIST (interval);
            """
            conn.execute(text(create_table_sql))
            logger.info("Created ohlcv_data table")

            # Create initial partitions for supported intervals
            for interval in config.supported_intervals:
                # Use a safe partition name that handles minutes vs months to avoid case-folding collisions
                safe_interval = interval
                if interval == '1M':
                    safe_interval = '1month'
                elif interval.endswith('m'):
                    safe_interval = interval.replace('m', 'min')
                elif interval.endswith('h'):
                    safe_interval = interval.replace('h', 'hour')
                elif interval.endswith('d'):
                    safe_interval = interval.replace('d', 'day')
                elif interval.endswith('w'):
                    safe_interval = interval.replace('w', 'week')
                
                partition_name = f"ohlcv_data_{safe_interval.lower()}"

                # Drop existing partition if recreating
                if drop_existing:
                    conn.execute(text(f"DROP TABLE IF EXISTS {partition_name} CASCADE"))

                # Create interval partition
                create_partition_sql = f"""
                CREATE TABLE IF NOT EXISTS {partition_name}
                PARTITION OF ohlcv_data FOR VALUES IN ('{interval}');
                """
                conn.execute(text(create_partition_sql))
                logger.info(f"Created partition: {partition_name} for interval {interval}")

            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_interval_timestamp ON ohlcv_data (symbol, interval, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_interval ON ohlcv_data (symbol, interval)",
                "CREATE INDEX IF NOT EXISTS idx_ohlcv_timestamp ON ohlcv_data (timestamp)"
            ]

            for index_sql in indexes:
                conn.execute(text(index_sql))

            logger.info("Created database indexes")
            conn.commit()

    except Exception as e:
        logger.error(f"Schema setup failed: {e}")
        raise

    finally:
        engine.dispose()

def test_connection(config: PostgresConfig) -> bool:
    """
    Test database connection.

    Args:
        config: Database configuration

    Returns:
        True if connection successful
    """
    from sqlalchemy import create_engine, text

    try:
        engine = create_engine(config.get_connection_string())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False