#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script

This script sets up the PostgreSQL database schema for OHLCV data storage,
including tables, partitions, indexes, and initial configuration.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from postgres_config import PostgresConfig, setup_database_schema, test_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(
        description='Set up PostgreSQL database for OHLCV storage'
    )

    # Configuration options
    parser.add_argument(
        '--config',
        type=str,
        help='Configuration file path (JSON)'
    )

    parser.add_argument(
        '--env',
        action='store_true',
        help='Use environment variables for configuration'
    )

    # Database options
    parser.add_argument(
        '--host',
        type=str,
        help='PostgreSQL host'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=5432,
        help='PostgreSQL port (default: 5432)'
    )

    parser.add_argument(
        '--database',
        type=str,
        help='Database name'
    )

    parser.add_argument(
        '--user',
        type=str,
        help='Database user'
    )

    parser.add_argument(
        '--password',
        type=str,
        help='Database password'
    )

    parser.add_argument(
        '--ssl-mode',
        type=str,
        default='require',
        choices=['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'],
        help='SSL mode (default: require)'
    )

    # Setup options
    parser.add_argument(
        '--drop-existing',
        action='store_true',
        help='Drop existing tables before creating new ones'
    )

    parser.add_argument(
        '--test-only',
        action='store_true',
        help='Only test connection, do not create schema'
    )

    parser.add_argument(
        '--create-partitions',
        action='store_true',
        help='Create monthly partitions for recent data'
    )

    args = parser.parse_args()

    try:
        # Load configuration
        if args.env:
            logger.info("Loading configuration from environment variables")
            config = PostgresConfig.from_env()
        elif args.config:
            logger.info(f"Loading configuration from file: {args.config}")
            config = PostgresConfig.from_file(args.config)
        else:
            # Use command line arguments
            logger.info("Using command line configuration")
            config = PostgresConfig(
                host=args.host,
                port=args.port,
                database=args.database,
                user=args.user,
                password=args.password,
                ssl_mode=args.ssl_mode
            )

        # Validate configuration
        config.validate()
        logger.info("Configuration validated successfully")

        # Test connection
        logger.info("Testing database connection...")
        if not test_connection(config):
            logger.error("Database connection test failed")
            sys.exit(1)

        if args.test_only:
            logger.info("Connection test successful. Exiting (--test-only specified)")
            sys.exit(0)

        # Setup database schema
        logger.info("Setting up database schema...")
        setup_database_schema(config, drop_existing=args.drop_existing)

        if args.create_partitions:
            logger.info("Creating monthly partitions...")
            create_monthly_partitions(config)

        logger.info("Database setup completed successfully!")

        # Print connection info
        print("\nDatabase setup complete!")
        print(f"Host: {config.host}:{config.port}")
        print(f"Database: {config.database}")
        print(f"Schema: {config.schema_name}")
        print("\nYou can now use the PostgreSQL storage with:")
        print(f"from scripts.postgres_storage import PostgreSQLStorage")
        print(f"storage = PostgreSQLStorage.from_config(config)")

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

def create_monthly_partitions(config: PostgresConfig) -> None:
    """
    Create monthly partitions for recent data.

    Args:
        config: Database configuration
    """
    from sqlalchemy import create_engine, text
    from datetime import datetime, timedelta

    engine = create_engine(config.get_connection_string())

    try:
        with engine.connect() as conn:
            # Create partitions for next 12 months
            today = datetime.utcnow().replace(day=1)  # First day of current month

            for i in range(12):
                partition_date = today + timedelta(days=30 * i)
                year = partition_date.year
                month = partition_date.month

                # Create partition for each interval
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
                    
                    base_partition_name = f"ohlcv_data_{safe_interval.lower()}"
                    partition_name = f"{base_partition_name}_{year}_{month:02d}"

                    start_date = partition_date
                    end_date = start_date + timedelta(days=30)

                    create_partition_sql = f"""
                    CREATE TABLE IF NOT EXISTS {partition_name}
                    PARTITION OF {base_partition_name}
                    FOR VALUES FROM ('{start_date.isoformat()}') TO ('{end_date.isoformat()}');
                    """

                    try:
                        conn.execute(text(create_partition_sql))
                        logger.info(f"Created partition: {partition_name}")
                    except Exception as e:
                        logger.warning(f"Failed to create partition {partition_name}: {e}")

            conn.commit()

    except Exception as e:
        logger.error(f"Failed to create monthly partitions: {e}")
        raise

    finally:
        engine.dispose()

if __name__ == '__main__':
    main()