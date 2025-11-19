#!/usr/bin/env python3
"""
Test script for data integrity validation functions.
"""

import pandas as pd
import sys
import os

# Add the scripts directory to the path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from okx_data_collector import validate_data_continuity

def test_validate_data_continuity():
    """Test the validate_data_continuity function with various scenarios."""

    print("Testing validate_data_continuity function...")

    # Test 1: Empty DataFrame
    empty_df = pd.DataFrame()
    assert not validate_data_continuity(empty_df), "Empty DataFrame should return False"
    print("✓ Test 1 passed: Empty DataFrame")

    # Test 2: DataFrame without timestamp column
    no_ts_df = pd.DataFrame({'price': [1, 2, 3]})
    assert not validate_data_continuity(no_ts_df), "DataFrame without timestamp should return False"
    print("✓ Test 2 passed: No timestamp column")

    # Test 3: Single data point
    single_point_df = pd.DataFrame({
        'timestamp': [pd.Timestamp('2024-01-01 00:00:00')]
    })
    assert validate_data_continuity(single_point_df), "Single data point should be considered continuous"
    print("✓ Test 3 passed: Single data point")

    # Test 4: Continuous data (1-minute intervals)
    continuous_timestamps = pd.date_range('2024-01-01 00:00:00', periods=10, freq='1min')
    continuous_df = pd.DataFrame({
        'timestamp': continuous_timestamps,
        'price': range(10)
    })
    assert validate_data_continuity(continuous_df, interval_minutes=1), "Continuous data should pass validation"
    print("✓ Test 4 passed: Continuous data")

    # Test 5: Data with gaps
    gap_timestamps = [
        pd.Timestamp('2024-01-01 00:00:00'),
        pd.Timestamp('2024-01-01 00:01:00'),
        pd.Timestamp('2024-01-01 00:05:00'),  # Gap of 4 minutes (should fail)
    ]
    gap_df = pd.DataFrame({
        'timestamp': gap_timestamps,
        'price': [1, 2, 3]
    })
    assert not validate_data_continuity(gap_df, interval_minutes=1), "Data with gaps should fail validation"
    print("✓ Test 5 passed: Data with gaps")

    # Test 6: Data with duplicates
    dup_timestamps = [
        pd.Timestamp('2024-01-01 00:00:00'),
        pd.Timestamp('2024-01-01 00:01:00'),
        pd.Timestamp('2024-01-01 00:01:00'),  # Duplicate
        pd.Timestamp('2024-01-01 00:02:00'),
    ]
    dup_df = pd.DataFrame({
        'timestamp': dup_timestamps,
        'price': [1, 2, 2, 3]
    })
    assert not validate_data_continuity(dup_df, interval_minutes=1), "Data with duplicates should fail validation"
    print("✓ Test 6 passed: Data with duplicates")

    # Test 7: Low coverage data
    sparse_timestamps = pd.date_range('2024-01-01 00:00:00', periods=5, freq='10min')  # Only 5 points over ~40 minutes
    sparse_df = pd.DataFrame({
        'timestamp': sparse_timestamps,
        'price': range(5)
    })
    assert not validate_data_continuity(sparse_df, interval_minutes=1), "Low coverage data should fail validation"
    print("✓ Test 7 passed: Low coverage data")

    print("\nAll tests passed! ✓")

if __name__ == "__main__":
    test_validate_data_continuity()