import pytest
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
from datetime import datetime
import ccxt.async_support as ccxt
import sys
from pathlib import Path

# Ensure examples directory is in Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.collect_okx_ohlcv import CryptoCollector

def test_collector_initialization():
    """Test basic collector setup"""
    collector = CryptoCollector(
        exchange_id="okx",
        interval="15min"
    )
    assert collector.exchange_id == "okx"
    assert collector.interval == "15min"
    assert collector.exchange is not None

@pytest.mark.asyncio
async def test_rate_limit_handling():
    """Test rate limit handling behavior"""
    with patch('ccxt.async_support.okx') as mock_exchange_class:
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv = AsyncMock(side_effect=[
            ccxt.RateLimitExceeded("Rate limit"),  # First call fails
            [[1641024000000, 46000, 46100, 45900, 46050, 100]]  # Second succeeds
        ])
        mock_exchange_class.return_value = mock_exchange
        
        collector = CryptoCollector(exchange_id="okx", interval="15m")
        
        # Should retry and succeed
        data = await collector.fetch_data(
            symbol="BTC/USDT",
            start=datetime(2022, 1, 1),
            end=datetime(2022, 1, 2)
        )
        assert len(mock_exchange.fetch_ohlcv.call_args_list) == 2
        
        assert isinstance(data, pd.DataFrame)
        assert 'open' in data.columns

@pytest.mark.asyncio
async def test_collector_basic():
    """Test basic collector functionality"""
    collector = CryptoCollector(exchange_id="okx", interval="15min")
    assert collector.exchange_id == "okx"
    assert collector.interval == "15min"

@pytest.mark.asyncio
async def test_fetch_data_success():
    """Test successful data fetch"""
    mock_data = [
        [1641024000000, 46000, 46100, 45900, 46050, 100],
        [1641025800000, 46050, 46200, 46000, 46100, 200]
    ]
    
    with patch('ccxt.async_support.okx') as mock_exchange_class:
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=mock_data)
        mock_exchange_class.return_value = mock_exchange
        
        collector = CryptoCollector(exchange_id="okx", interval="15min")
        data = await collector.fetch_data(
            symbol="BTC/USDT",
            start=datetime(2022, 1, 1),
            end=datetime(2022, 1, 2)
        )
        
        # Verify mock was called with correct parameters
        mock_exchange.fetch_ohlcv.assert_called_once()
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 2
        assert list(data.columns) == ['open', 'high', 'low', 'close', 'volume']

@pytest.mark.asyncio
async def test_process_raw_data():
    """Test data processing"""
    collector = CryptoCollector(exchange_id="okx", interval="15min")
    raw_data = [
        [1641024000000, 46000, 46100, 45900, 46050, 100]
    ]

    df = collector._process_raw_data(raw_data)
    assert df.index.name == 'timestamp'
    assert df.index[0].timestamp() == 1641024000

@pytest.mark.asyncio
async def test_fetch_data_max_retries_exceeded():
    """Test when max retries are exceeded for rate limit"""
    with patch('ccxt.async_support.okx') as mock_exchange_class:
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv = AsyncMock(side_effect=ccxt.RateLimitExceeded("Rate limit"))
        mock_exchange_class.return_value = mock_exchange

        collector = CryptoCollector(exchange_id="okx", interval="15m")

        with pytest.raises(ccxt.RateLimitExceeded):
            await collector.fetch_data(
                symbol="BTC/USDT",
                start=datetime(2022, 1, 1),
                end=datetime(2022, 1, 2)
            )
        # Should have called 3 times (max_retries)
        assert len(mock_exchange.fetch_ohlcv.call_args_list) == 3

@pytest.mark.asyncio
async def test_fetch_data_other_exception():
    """Test handling of non-rate-limit exceptions"""
    with patch('ccxt.async_support.okx') as mock_exchange_class:
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv = AsyncMock(side_effect=Exception("Other error"))
        mock_exchange_class.return_value = mock_exchange

        collector = CryptoCollector(exchange_id="okx", interval="15m")

        with pytest.raises(Exception):
            await collector.fetch_data(
                symbol="BTC/USDT",
                start=datetime(2022, 1, 1),
                end=datetime(2022, 1, 2)
            )
        # Should have called once, since not rate limit
        assert len(mock_exchange.fetch_ohlcv.call_args_list) == 1

def test_main():
    """Test main function"""
    from examples.collect_okx_ohlcv import main
    main()  # Should do nothing
