#!/usr/bin/env python3
"""
Data Quality Check Script for Crypto Trading Data

This script performs comprehensive checks on the prepared crypto data
before running the trading workflow.
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.config_manager import ConfigManager

def check_data_quality(skip_calendar_check=False):
    """Perform comprehensive data quality checks.
    
    Args:
        skip_calendar_check: If True, skip calendar directory checks (for crypto mode)
    """
    print("🔍 Performing Data Quality Checks...")

    config_manager = ConfigManager()
    data_config = config_manager.config.get('data', {})
    bin_data_dir = data_config.get('bin_data_dir', 'data/qlib_data/crypto')

    data_path = project_root / bin_data_dir

    if not data_path.exists():
        print(f"❌ Data directory not found: {data_path}")
        return False

    print(f"✅ Data directory found: {data_path}")

    # Check instruments
    instruments_file = data_path / "instruments" / "all.txt"
    if not instruments_file.exists():
        print(f"❌ Instruments file not found: {instruments_file}")
        return False

    instruments = []
    with open(instruments_file, 'r') as f:
        for line in f:
            if line.strip():
                parts = line.strip().split('\t')
                if len(parts) >= 1:
                    instruments.append(parts[0])

    print(f"✅ Found {len(instruments)} instruments: {instruments[:5]}...")

    # Check features directory
    features_dir = data_path / "features"
    if not features_dir.exists():
        print(f"❌ Features directory not found: {features_dir}")
        return False

    feature_counts = {}
    total_files = 0

    for instrument_dir in features_dir.iterdir():
        if instrument_dir.is_dir():
            instrument = instrument_dir.name.upper()
            bin_files = list(instrument_dir.glob("*.bin"))
            feature_counts[instrument] = len(bin_files)
            total_files += len(bin_files)

    print(f"✅ Total feature files: {total_files}")
    print(f"✅ Features per instrument: {dict(list(feature_counts.items())[:3])}...")

    # Check if we have enough features (should be more than basic OHLCV)
    min_expected_features = 8  # OHLCV + some technical indicators
    instruments_with_few_features = [inst for inst, count in feature_counts.items() if count < min_expected_features]

    if instruments_with_few_features:
        print(f"⚠️  Warning: Some instruments have few features: {instruments_with_few_features}")
        print("This may indicate feature generation issues.")
    else:
        print("✅ All instruments have sufficient features")

    # Check calendars
    calendars_dir = data_path / "calendars"
    if not calendars_dir.exists():
        if skip_calendar_check:
            print("ℹ️  Calendars directory not found (skipped for crypto mode)")
        else:
            print(f"❌ Calendars directory not found: {calendars_dir}")
            return False

    if calendars_dir.exists():
        calendar_files = list(calendars_dir.glob("*.txt"))
        if not calendar_files:
            if skip_calendar_check:
                print("ℹ️  No calendar files found (skipped for crypto mode)")
            else:
                print("❌ No calendar files found")
                return False

        print(f"✅ Found {len(calendar_files)} calendar files")

    # Check date ranges
    workflow_config = config_manager.get_workflow_config()
    expected_start = pd.Timestamp(workflow_config['start_time'])
    expected_end = pd.Timestamp(workflow_config['end_time'])

    print(f"📅 Expected date range: {expected_start} to {expected_end}")

    # Sample check of one instrument's data
    if instruments:
        sample_instrument = instruments[0].lower()
        sample_dir = features_dir / sample_instrument

        if sample_dir.exists():
            # Try to load close price data
            close_file = sample_dir / "close.15min.bin"
            if close_file.exists():
                try:
                    # This is a simplified check - in real qlib we'd use proper loading
                    file_size = close_file.stat().st_size
                    print(f"✅ Sample data file size: {file_size} bytes for {sample_instrument}")
                except Exception as e:
                    print(f"⚠️  Could not check sample data: {e}")

    print("🎉 Data quality checks completed!")
    return True

if __name__ == "__main__":
    success = check_data_quality()
    if not success:
        print("❌ Data quality issues found. Please fix before running workflow.")
        sys.exit(1)
    else:
        print("✅ Data quality checks passed. Ready to run workflow.")