import os
import sys
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

"""Ignore RL tests on non-linux platform."""
collect_ignore = []

if sys.platform != "linux":
    for root, dirs, files in os.walk("rl"):
        for file in files:
            collect_ignore.append(os.path.join(root, file))

@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary test data directory"""
    return tmp_path / "qlib_data"

@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data with known patterns"""
    dates = pd.date_range("2024-01-01", "2024-01-02", freq="15min", tz="UTC")
    data = pd.DataFrame({
        "timestamp": dates,
        "open": np.random.random(len(dates)) * 100 + 40000,
        "high": np.random.random(len(dates)) * 100 + 40100,
        "low": np.random.random(len(dates)) * 100 + 39900,
        "close": np.random.random(len(dates)) * 100 + 40000,
        "volume": np.random.random(len(dates)) * 1000
    })
    # Add some known patterns
    data.loc[data.index[10:15], "close"] *= 1.3  # Price spike
    data.loc[data.index[20:25], "volume"] *= 10  # Volume spike
    # Introduce missing data but below threshold (5% is about 5 rows, we have 3)
    data.loc[data.index[30:33], "close"] = np.nan  # Missing data
    return data

@pytest.fixture
def config_for_test():
    """Test configuration"""
    return {
        "data_collection": {
            "exchange": "okx",
            "interval": "15min",
            "api": {"rate_limit": 20}
        },
        "data_validation": {
            "missing_threshold": 0.05,
            "outliers": {
                "price_jump": 0.30,
                "volume_spike": 10.0
            }
        }
    }
