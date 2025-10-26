import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from qlib.utils.io import write_parquet, read_parquet

@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data for testing"""
    dates = pd.date_range("2024-01-01", "2024-01-02", freq="15min", tz="UTC")
    return pd.DataFrame({
        "open": np.random.random(len(dates)) * 100 + 40000,
        "high": np.random.random(len(dates)) * 100 + 40100,
        "low": np.random.random(len(dates)) * 100 + 39900,
        "close": np.random.random(len(dates)) * 100 + 40000,
        "volume": np.random.random(len(dates)) * 1000
    }, index=dates)

def test_parquet_roundtrip(tmp_path, sample_ohlcv_data):
    """Test writing and reading Parquet files"""
    file_path = tmp_path / "test.parquet"
    
    # Write data
    write_parquet(sample_ohlcv_data, file_path)
    assert file_path.exists()
    
    # Read back
    df_read = read_parquet(file_path)
    
    # Verify data integrity
    pd.testing.assert_frame_equal(sample_ohlcv_data, df_read)
    assert df_read.index.tz == sample_ohlcv_data.index.tz

def test_parquet_compression(tmp_path, sample_ohlcv_data):
    """Test Parquet compression options"""
    uncompressed = tmp_path / "uncompressed.parquet"
    compressed = tmp_path / "compressed.parquet"
    
    write_parquet(sample_ohlcv_data, uncompressed, compression=None)
    write_parquet(sample_ohlcv_data, compressed, compression="snappy")
    
    assert compressed.stat().st_size < uncompressed.stat().st_size
    pd.testing.assert_frame_equal(
        read_parquet(compressed),
        read_parquet(uncompressed)
    )
