import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
import json
import ccxt
import asyncio

from qlib.scripts.data_collector.crypto.collector import CryptoCollector

def test_okx_collector_init():
    """Test collector initialization with config"""
    collector = CryptoCollector(save_dir="/tmp/qlib_data", interval="15min")
    assert collector.interval == "15min"
    assert collector._timezone == "UTC"

@pytest.fixture
def mock_ohlcv_data():
    """Generate mock OHLCV data"""
    dates = pd.date_range("2024-01-01", "2024-01-02", freq="15min", tz="UTC")
    data = pd.DataFrame({
        "timestamp": dates,
        "open": np.random.random(len(dates)) * 100 + 40000,
        "high": np.random.random(len(dates)) * 100 + 40100,
        "low": np.random.random(len(dates)) * 100 + 39900,
        "close": np.random.random(len(dates)) * 100 + 40000,
        "volume": np.random.random(len(dates)) * 1000
    })
    return data

@pytest.mark.asyncio
async def test_fetch_data(mock_ohlcv_data):
    """Test data fetching with mock response"""
    with patch("ccxt.okx") as mock_okx:
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv.return_value = asyncio.Future()
        mock_exchange.fetch_ohlcv.return_value.set_result(mock_ohlcv_data.values.tolist())
        mock_okx.return_value = mock_exchange
        
        collector = CryptoCollector(save_dir="/tmp/qlib_data", interval="15min")
        collector.exchange = mock_exchange
        data = await collector.get_data(
            symbol="BTC/USDT",
            interval="15min",
            start_datetime=pd.Timestamp("2024-01-01", tz="UTC"),
            end_datetime=pd.Timestamp("2024-01-02", tz="UTC")
        )
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) == len(mock_ohlcv_data)
        assert all(col in data.columns for col in ["open", "high", "low", "close", "volume"])
        assert data.index.freq == "15min"

@pytest.mark.asyncio
async def test_fetch_data_rate_limit_retry(mock_ohlcv_data):
    """Test rate limit handling and retry logic"""
    with patch("ccxt.okx") as mock_okx:
        mock_exchange = Mock()
        # First call raises rate limit, second succeeds
        future = asyncio.Future()
        future.set_result(mock_ohlcv_data.values.tolist())
        mock_exchange.fetch_ohlcv.side_effect = [
            ccxt.RateLimitExceeded("Rate limit exceeded"),
            future
        ]
        mock_okx.return_value = mock_exchange

        collector = CryptoCollector(save_dir="/tmp/qlib_data", interval="15min")
        collector.exchange = mock_exchange
        data = await collector.get_data(
            symbol="BTC/USDT",
            interval="15min",
            start_datetime=pd.Timestamp("2024-01-01", tz="UTC"),
            end_datetime=pd.Timestamp("2024-01-02", tz="UTC")
        )

        assert isinstance(data, pd.DataFrame)
        assert mock_exchange.fetch_ohlcv.call_count == 2

def test_data_validation():
    """Test data validation rules"""
    collector = CryptoCollector(save_dir="/tmp/qlib_data", interval="15min")
    
    # Test missing data threshold
    dates = pd.date_range("2024-01-01", "2024-01-02", freq="15min", tz="UTC")
    data = pd.DataFrame(index=dates)
    data["close"] = 40000
    data.iloc[5:10, 0] = np.nan
    
    with pytest.raises(ValueError, match="Missing data exceeds threshold"):
        collector.validate_data(data)

def test_data_validation_edge_cases(sample_ohlcv_data, config_for_test):
    """Test various data validation scenarios"""
    collector = CryptoCollector(save_dir="/tmp/qlib_data", interval="15min")

    # Test price spike detection
    df = sample_ohlcv_data.copy()
    df.set_index("timestamp", inplace=True)
    result, report = collector.validate_data(df)
    assert report["outliers_detected"] >= 5  # Price spike window

    # Test volume spike detection
    assert "is_outlier" in result.columns
    assert result["is_outlier"].sum() >= 5  # Combined price and volume spikes

    # Test gap detection
    df = sample_ohlcv_data.copy()
    df.set_index("timestamp", inplace=True)
    df = df.drop(df.index[40:45])  # Create gap
    result, report = collector.validate_data(df)
    assert "gaps_detected" in report
    assert report["gaps_detected"] == 5

def test_data_persistence(test_data_dir, mock_ohlcv_data):
    """Test data saving and loading with manifest"""
    collector = CryptoCollector(save_dir=test_data_dir, interval="15min")
    
    # Save data
    symbol = "BTC-USDT"
    collector.save_data(mock_ohlcv_data, symbol=symbol)
    
    # Verify file structure
    data_path = test_data_dir / "okx" / symbol / "15min"
    assert data_path.exists()
    
    # Check manifest content
    with open(data_path / "manifest.json") as f:
        manifest = json.load(f)
        assert manifest["symbol"] == symbol
        assert manifest["interval"] == "15min"
        assert manifest["row_count"] == len(mock_ohlcv_data)
    
    # Verify data integrity
    saved_data = pd.read_parquet(data_path / f"{mock_ohlcv_data.index[0].strftime('%Y-%m-%d')}.parquet")
    # Check that saved data is subset of original (due to date grouping)
    assert len(saved_data) <= len(mock_ohlcv_data)
    assert all(col in saved_data.columns for col in mock_ohlcv_data.columns)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_collection_workflow(test_data_dir, config_for_test):
    """Test complete data collection workflow"""
    collector = CryptoCollector(
        save_dir=test_data_dir,
        interval="15min"
    )

    # Test collection and storage
    symbol = "BTC/USDT"
    start_date = pd.Timestamp("2024-01-01", tz="UTC")
    end_date = pd.Timestamp("2024-01-02", tz="UTC")

    # Mock the exchange to avoid real API calls
    with patch("ccxt.okx") as mock_okx:
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv.return_value = asyncio.Future()
        mock_exchange.fetch_ohlcv.return_value.set_result([
            [1704067200000, 40000, 40100, 39900, 40050, 1000],
            [1704068100000, 40050, 40200, 40000, 40100, 1100]
        ])
        mock_okx.return_value = mock_exchange
        collector.exchange = mock_exchange

        await collector.download_data(
            symbol=symbol,
            start_datetime=start_date,
            end_datetime=end_date
        )

    # Verify file structure
    data_path = test_data_dir / "okx" / "BTC-USDT" / "15min"
    assert data_path.exists()

    # Check manifest
    manifest_path = data_path / "manifest.json"
    assert manifest_path.exists()

    # Verify data quality
    data_files = list(data_path.glob("*.parquet"))
    assert len(data_files) > 0

    df = pd.read_parquet(data_files[0])
    assert len(df) > 0  # Data was saved
