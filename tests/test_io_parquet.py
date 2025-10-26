import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from qlib.utils.io import write_parquet, read_parquet

@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data for testing"""
    dates = pd.date_range("2024-01-01", "2024-01-10", freq="1min", tz="UTC")
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

def test_parquet_no_timezone(tmp_path):
    """Test Parquet I/O with DataFrame without timezone"""
    dates = pd.date_range("2024-01-01", periods=10, freq="1H")
    df = pd.DataFrame({
        "value": np.random.random(len(dates))
    }, index=dates)
    
    file_path = tmp_path / "no_tz.parquet"
    write_parquet(df, file_path)
    df_read = read_parquet(file_path)
    
    # Since no tz, write doesn't localize, read adds UTC
    expected_index = df.index.tz_localize("UTC")
    pd.testing.assert_frame_equal(df_read, df.set_index(expected_index))

def test_parquet_irregular_index(tmp_path):
    """Test Parquet I/O with irregular datetime index"""
    dates = pd.DatetimeIndex([
        "2024-01-01 00:00:00",
        "2024-01-01 00:05:00",
        "2024-01-01 00:10:00",
        "2024-01-01 00:20:00",  # irregular
        "2024-01-01 00:30:00"
    ], tz="UTC")
    df = pd.DataFrame({
        "value": np.random.random(len(dates))
    }, index=dates)
    
    file_path = tmp_path / "irregular.parquet"
    write_parquet(df, file_path)
    df_read = read_parquet(file_path)
    
    # Irregular index, so no freq inferred
    pd.testing.assert_frame_equal(df_read, df)
    assert df_read.index.freq is None

def test_parquet_non_datetime_index(tmp_path):
    """Test Parquet I/O with non-datetime index"""
    df = pd.DataFrame({"value": [1, 2, 3]}, index=range(3))

    file_path = tmp_path / "non_dt.parquet"
    write_parquet(df, file_path)
    df_read = read_parquet(file_path)

    pd.testing.assert_frame_equal(df_read, df)

def test_parquet_small_datetime_index(tmp_path):
    """Test Parquet I/O with small datetime index to trigger infer_freq ValueError"""
    dates = pd.DatetimeIndex(["2024-01-01 00:00:00", "2024-01-02 00:00:00"], tz="UTC")
    df = pd.DataFrame({"value": [1, 2]}, index=dates)

    file_path = tmp_path / "small_dt.parquet"
    write_parquet(df, file_path)
    df_read = read_parquet(file_path)

    # Since only 2 dates, infer_freq raises ValueError, so freq should not be set
    assert df_read.index.freq is None
    pd.testing.assert_frame_equal(df_read, df)
