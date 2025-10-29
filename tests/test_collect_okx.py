import os
import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
import json
import ccxt
import asyncio
import tempfile
import yaml
import sys

from qlib.scripts.data_collector.crypto.collector import CryptoCollector

class MockExchange:
    def __init__(self, mock_data):
        self.mock_data = mock_data
        self.counter = 0

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None):
        if self.counter == 0:
            self.counter += 1
            return self.mock_data
        else:
            return []  # Return empty list to break the loop

'''

Run all tests in test_collect_okx.py
Generate coverage for the collector and manifest modules
Show missing lines in terminal output
Create HTML coverage report in coverage_html/
Use the .coveragerc configuration for proper source mapping

pytest tests/test_collect_okx.py -v \
    --cov=qlib.examples.collect_okx_ohlcv \
    --cov=qlib.features.crypto_workflow.manifest \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-config=.coveragerc

'''


# Add project root to path
root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from examples.collect_okx_ohlcv import OKXCollector

def test_okx_collector_init():
    """Test collector initialization with config"""
    collector = CryptoCollector(save_dir="/tmp/qlib_data", interval="15min", qlib_home="/home/watson/work/qlib")
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
        
        collector = CryptoCollector(save_dir="/tmp/qlib_data", interval="15min", qlib_home="/home/watson/work/qlib")
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

        collector = CryptoCollector(save_dir="/tmp/qlib_data", interval="15min", qlib_home="/home/watson/work/qlib")
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
    collector = CryptoCollector(save_dir="/tmp/qlib_data", interval="15min", qlib_home="/home/watson/work/qlib")
    
    # Test missing data threshold
    dates = pd.date_range("2024-01-01", "2024-01-02", freq="15min", tz="UTC")
    data = pd.DataFrame(index=dates)
    data["close"] = 40000
    data.iloc[5:10, 0] = np.nan
    
    with pytest.raises(ValueError, match="Missing data exceeds threshold"):
        collector.validate_data(data)

def test_data_validation_edge_cases(sample_ohlcv_data, config_for_test):
    """Test various data validation scenarios"""
    collector = CryptoCollector(save_dir="/tmp/qlib_data", interval="15min", qlib_home="/home/watson/work/qlib")

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

    import os
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

    import os
    collector = CryptoCollector(
        save_dir=test_data_dir,
        interval="15min"
    )

    # Test collection and storage
    symbol = "BTC/USDT"
    start_date = pd.Timestamp("2024-01-01", tz="UTC")
    end_date = pd.Timestamp("2024-01-02", tz="UTC")


@pytest.mark.asyncio
async def test_okx_collector_workflow():
    """Test OKXCollector workflow"""
    collector = OKXCollector()
    assert collector is not None
    # Add more test logic here if needed

    # Mock the exchange to avoid real API calls
    with patch("ccxt.okx") as mock_okx:
        mock_exchange = Mock()
        # Create futures: first call returns data, subsequent calls return empty list
        future_with_data = asyncio.Future()
        future_with_data.set_result([
            [1704067200000, 40000, 40100, 39900, 40050, 1000],
            [1704068100000, 40050, 40200, 40000, 40100, 1100]
        ])
        future_empty = asyncio.Future()
        future_empty.set_result([])
        mock_exchange.fetch_ohlcv.side_effect = [future_with_data, future_empty]
        mock_okx.return_value = mock_exchange
        collector.exchange = mock_exchange

        # Define test variables
        symbol = "BTC/USDT"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)
        output_path = Path("/tmp/test_output.parquet")

        await collector.download_data(
            symbol=symbol,
            start_datetime=start_date,
            end_datetime=end_date,
            output_path=output_path
        )

    # Verify output file exists
    assert output_path.exists()

    # Load and verify data
    df = pd.read_parquet(output_path)
    assert len(df) == 2  # Should have the two rows from the mock data
    assert all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])

def test_collect_historical():
    # Mock data
    mock_data = [
        [1640995200000, 46813.21, 46937.91, 46761.32, 46850.23, 1234.56],  # 2022-01-01
        [1640998800000, 46850.23, 47100.45, 46825.12, 47050.78, 987.65],
        [1641002400000, 47050.78, 47200.00, 46900.00, 47150.34, 765.43]
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "btc_usdt_1h.parquet"

        # Create collector with mock exchange
        collector = OKXCollector()
        collector.exchange = MockExchange(mock_data)

        # Collect data
        df = collector.collect_historical(
            symbol="BTC/USDT",
            timeframe="1h",
            start_time=datetime(2022, 1, 1),
            end_time=datetime(2022, 1, 1, 1),  # Shorten end_time to ensure loop exits
            output_path=output_path
        )

        # Verify DataFrame
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(mock_data)
        assert all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])

        # Verify parquet file
        assert output_path.exists()
        loaded_df = pd.read_parquet(output_path)
        pd.testing.assert_frame_equal(df, loaded_df)

        # Verify manifest
        manifest_path = output_path.parent / 'manifest.yaml'
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        assert output_path.name in manifest
        entry = manifest[output_path.name]
        assert all(k in entry for k in ['symbol', 'timeframe', 'start_ts', 'end_ts', 'row_count', 'file_hash'])

@pytest.mark.asyncio
async def test_download_data_error_handling():
    """Test error handling in download_data method"""
    collector = OKXCollector()

    # Mock exchange to raise an exception
    with patch("ccxt.okx") as mock_okx:
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv.side_effect = Exception("API Error")
        mock_okx.return_value = mock_exchange
        collector.exchange = mock_exchange

        with pytest.raises(Exception, match="API Error"):
            await collector.download_data(
                symbol="BTC/USDT",
                start_datetime=datetime(2024, 1, 1),
                end_datetime=datetime(2024, 1, 2),
                output_path=Path("/tmp/test_error.parquet")
            )

def test_main_function():
    """Test the main function with mocked arguments"""
    from examples.collect_okx_ohlcv import main
    import sys

    # Mock sys.argv
    original_argv = sys.argv
    try:
        sys.argv = [
            'collect_okx_ohlcv.py',
            '--symbol', 'BTC/USDT',
            '--start', '2024-01-01',
            '--end', '2024-01-02',
            '--output', '/tmp/test_output.parquet'
        ]

        with patch("examples.collect_okx_ohlcv.OKXCollector") as mock_collector_class:
            mock_collector = Mock()
            mock_collector_class.return_value = mock_collector

            # Call main function
            main()

            # Verify collector was created and collect_historical was called
            mock_collector_class.assert_called_once()
            mock_collector.collect_historical.assert_called_once_with(
                symbol="BTC/USDT",
                timeframe="1h",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 2),
                output_path=Path("/tmp/test_output.parquet")
            )
    finally:
        sys.argv = original_argv
