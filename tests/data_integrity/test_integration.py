#!/usr/bin/env python3
"""
Integration test for data integrity validation in the data collection workflow.
"""

import pandas as pd
import tempfile
import os
import sys
from unittest.mock import Mock, patch

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

def test_data_integrity_workflow():
    """Test the data integrity validation workflow in update_latest_data."""

    print("Testing data integrity validation workflow...")

    # Create mock data with gaps
    corrupted_timestamps = [
        pd.Timestamp('2024-01-01 00:00:00'),
        pd.Timestamp('2024-01-01 00:01:00'),
        pd.Timestamp('2024-01-01 00:05:00'),  # Gap
        pd.Timestamp('2024-01-01 00:06:00'),
    ]
    corrupted_df = pd.DataFrame({
        'timestamp': corrupted_timestamps,
        'open': [100, 101, 105, 106],
        'high': [102, 103, 107, 108],
        'low': [99, 100, 104, 105],
        'close': [101, 102, 106, 107],
        'volume': [1000, 1100, 1200, 1300]
    })

    # Test CSV validation
    from okx_data_collector import validate_data_continuity

    is_valid = validate_data_continuity(corrupted_df, interval_minutes=1)
    assert not is_valid, "Corrupted data should fail validation"
    print("✓ CSV data integrity validation works correctly")

    # Test with good data
    good_timestamps = pd.date_range('2024-01-01 00:00:00', periods=5, freq='1min')
    good_df = pd.DataFrame({
        'timestamp': good_timestamps,
        'open': [100, 101, 102, 103, 104],
        'high': [102, 103, 104, 105, 106],
        'low': [99, 100, 101, 102, 103],
        'close': [101, 102, 103, 104, 105],
        'volume': [1000, 1100, 1200, 1300, 1400]
    })

    is_valid_good = validate_data_continuity(good_df, interval_minutes=1)
    assert is_valid_good, "Good data should pass validation"
    print("✓ Good CSV data passes validation")

    # Test database validation (using SQLite for testing)
    from okx_data_collector import validate_database_continuity
    from sqlalchemy import create_engine, text
    import sqlite3

    # Create in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")

    # Create test table
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE ohlcv_data (
            symbol TEXT,
            timestamp TIMESTAMP,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            interval TEXT
        )
        """))

        # Insert corrupted data (with gaps)
        for _, row in corrupted_df.iterrows():
            conn.execute(text("""
            INSERT INTO ohlcv_data (symbol, timestamp, open, high, low, close, volume, interval)
            VALUES (:symbol, :timestamp, :open, :high, :low, :close, :volume, :interval)
            """), {
                'symbol': 'BTC/USDT',
                'timestamp': row['timestamp'].to_pydatetime(),  # Convert to datetime
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume'],
                'interval': '1m'
            })
        conn.commit()

    # Test database validation with corrupted data
    db_valid = validate_database_continuity(engine, "ohlcv_data", "BTC/USDT", interval_minutes=1)
    assert not db_valid, "Corrupted database data should fail validation"
    print("✓ Database data integrity validation works correctly")

    # Insert good data
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM ohlcv_data WHERE symbol = 'BTC/USDT'"))
        for _, row in good_df.iterrows():
            conn.execute(text("""
            INSERT INTO ohlcv_data (symbol, timestamp, open, high, low, close, volume, interval)
            VALUES (:symbol, :timestamp, :open, :high, :low, :close, :volume, :interval)
            """), {
                'symbol': 'BTC/USDT',
                'timestamp': row['timestamp'].to_pydatetime(),  # Convert to datetime
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume'],
                'interval': '1m'
            })
        conn.commit()

    # Test good database data
    db_valid_good = validate_database_continuity(engine, "ohlcv_data", "BTC/USDT", interval_minutes=1)
    assert db_valid_good, "Good database data should pass validation"
    print("✓ Good database data passes validation")

    print("\nAll integration tests passed! ✓")

if __name__ == "__main__":
    test_data_integrity_workflow()