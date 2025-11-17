#!/usr/bin/env python3
"""
Test script to verify database-mode incremental collection logic.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.okx_data_collector import calculate_fetch_window, get_last_timestamp_from_db, get_first_timestamp_from_db
from scripts.postgres_storage import PostgreSQLStorage
from scripts.postgres_config import PostgresConfig
from scripts.config_manager import ConfigManager
import pandas as pd

def test_database_timestamp_queries():
    """Test database timestamp query functions."""
    print("Testing database timestamp query functions...")

    # Load config
    config = ConfigManager("config/workflow.json").load_config()

    # Initialize PostgreSQL storage
    db_config = config.get("database", {})
    postgres_config = PostgresConfig(
        host=db_config.get("host", "localhost"),
        database=db_config.get("database", "qlib_crypto"),
        user=db_config.get("user", "crypto_user"),
        password=db_config.get("password", "change_me_in_production"),
        port=db_config.get("port", 5432)
    )

    postgres_storage = PostgreSQLStorage.from_config(postgres_config)

    # Test with a known symbol
    symbol = "BTC/USDT"
    interval = "1m"

    print(f"Testing with symbol: {symbol}, interval: {interval}")

    # Get timestamps
    last_ts = get_last_timestamp_from_db(symbol, interval, postgres_storage)
    first_ts = get_first_timestamp_from_db(symbol, interval, postgres_storage)

    print(f"Last timestamp: {last_ts}")
    print(f"First timestamp: {first_ts}")

    return postgres_storage

def test_calculate_fetch_window():
    """Test calculate_fetch_window with database mode."""
    print("\nTesting calculate_fetch_window with database mode...")

    postgres_storage = test_database_timestamp_queries()

    # Test parameters
    symbol = "BTC/USDT"
    requested_start = "2025-01-01T00:00:00Z"
    requested_end = pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    base_dir = "data/klines"
    interval = "1m"
    output_format = "postgres"

    print(f"Testing calculate_fetch_window with:")
    print(f"  symbol: {symbol}")
    print(f"  start: {requested_start}")
    print(f"  end: {requested_end}")
    print(f"  output_format: {output_format}")

    # Call the function
    adjusted_start, adjusted_end, should_fetch = calculate_fetch_window(
        symbol, requested_start, requested_end, base_dir, interval, output_format, postgres_storage
    )

    print(f"Result:")
    print(f"  adjusted_start: {adjusted_start}")
    print(f"  adjusted_end: {adjusted_end}")
    print(f"  should_fetch: {should_fetch}")

    return adjusted_start, adjusted_end, should_fetch

if __name__ == "__main__":
    try:
        test_calculate_fetch_window()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()