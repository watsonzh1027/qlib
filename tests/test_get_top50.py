import pytest
import json
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timezone, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.get_top50 import (
    get_okx_funding_top50,  # Keep for backward compatibility
    get_marketcap_top50,
    get_okx_swap_symbols,
    filter_top_swap_symbols,
    get_top50_by_marketcap,
    save_symbols,
    load_symbols,
    _load_cache,
    _save_cache
)

class TestGetTop50:
    
    @patch('ccxt.okx')
    def test_get_okx_funding_top50_success(self, mock_okx_class):
        """Test successful fetching and ranking of top 50 symbols."""
        # Mock CCXT exchange instance
        mock_exchange = MagicMock()
        mock_okx_class.return_value = mock_exchange
        
        # Mock funding rates data in CCXT format
        mock_funding_rates = {
            'BTC/USDT:USDT': {'fundingRate': 0.0001, 'nextFundingTime': 1640995200000},
            'ETH/USDT:USDT': {'fundingRate': -0.0002, 'nextFundingTime': 1640995200000},
            'ADA/USDT:USDT': {'fundingRate': 0.00005, 'nextFundingTime': 1640995200000}
        }
        mock_exchange.fetch_funding_rates.return_value = mock_funding_rates
        
        symbols = get_okx_funding_top50()
        
        # Should return symbols sorted by absolute funding rate
        assert symbols == ["ETH/USDT", "BTC/USDT", "ADA/USDT"]
        assert len(symbols) == 3
        
        # Verify CCXT was called correctly
        mock_okx_class.assert_called_once()
        mock_exchange.fetch_funding_rates.assert_called_once()
    
    @patch('ccxt.okx')
    def test_get_okx_funding_top50_api_error(self, mock_okx_class):
        """Test handling of API errors."""
        mock_exchange = MagicMock()
        mock_okx_class.return_value = mock_exchange
        mock_exchange.fetch_funding_rates.side_effect = Exception("API Error")
        
        symbols = get_okx_funding_top50()
        
        assert symbols == []
    
    @patch('ccxt.okx')
    def test_get_okx_funding_top50_empty_response(self, mock_okx_class):
        """Test handling of empty API response."""
        mock_exchange = MagicMock()
        mock_okx_class.return_value = mock_exchange
        mock_exchange.fetch_funding_rates.return_value = {}
        
        symbols = get_okx_funding_top50()
        
        assert symbols == []
    
    @patch('ccxt.okx')
    def test_get_okx_funding_top50_no_perpetuals(self, mock_okx_class):
        """Test handling when no perpetual swaps are found."""
        mock_exchange = MagicMock()
        mock_okx_class.return_value = mock_exchange
        mock_exchange.fetch_funding_rates.return_value = {
            'BTC/USDT': {'fundingRate': 0.0001}  # Spot, not perpetual
        }
        
        symbols = get_okx_funding_top50()
        
        assert symbols == []
    
    def test_save_symbols(self):
        """Test saving symbols to JSON file."""
        symbols = ["BTC/USDT", "ETH/USDT"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test_symbols.json")
            
            save_symbols(symbols, filepath)
            
            # Verify file was created and contains correct data
            assert os.path.exists(filepath)
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert data["symbols"] == symbols
            assert data["count"] == 2
            assert "updated_at" in data
    
    @patch('builtins.open')
    def test_save_symbols_io_error(self, mock_open):
        """Test handling of I/O errors during save."""
        mock_open.side_effect = IOError("Disk full")
        symbols = ["BTC/USDT"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test_symbols.json")
            
            save_symbols(symbols, filepath)
            
            # Should not raise, just log error
    
    def test_load_symbols_success(self):
        """Test loading symbols from JSON file."""
        symbols = ["BTC/USDT", "ETH/USDT"]
        data = {
            "symbols": symbols,
            "updated_at": "2025-01-01T00:00:00+00:00",
            "count": 2
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test_symbols.json")
            
            with open(filepath, 'w') as f:
                json.dump(data, f)
            
            loaded_symbols = load_symbols(filepath)
            
            assert loaded_symbols == symbols
    
    def test_load_symbols_file_not_found(self):
        """Test loading symbols when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "nonexistent.json")
            
            symbols = load_symbols(filepath)
            
            assert symbols == []
    
    def test_load_symbols_invalid_json(self):
        """Test loading symbols with invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "invalid.json")
            
            with open(filepath, 'w') as f:
                f.write("invalid json")
            
            symbols = load_symbols(filepath)
            
            assert symbols == []
    
    @patch('builtins.open')
    def test_load_symbols_io_error(self, mock_open):
        """Test handling of I/O errors during load."""
        mock_open.side_effect = IOError("Permission denied")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test_symbols.json")
            
            symbols = load_symbols(filepath)
            
            assert symbols == []
    
    @patch('ccxt.okx')
    def test_get_okx_funding_top50_integration(self, mock_okx_class):
        """Test integration of get_okx_funding_top50 with actual OKX exchange (mocked)."""
        mock_exchange = MagicMock()
        mock_okx_class.return_value = mock_exchange
        
        # Mocking a realistic response from OKX with 50 symbols
        mock_funding_rates = {
            f"SYM{i}/USDT:USDT": {"fundingRate": 0.0001 * i, "nextFundingTime": 1640995200000}
            for i in range(1, 51)
        }
        mock_exchange.fetch_funding_rates.return_value = mock_funding_rates
        
        result = get_okx_funding_top50()
        
        # Verify the number of symbols returned
        assert len(result) == 50
        
        # Verify the result is a list of symbols
        assert isinstance(result, list)
        assert all(isinstance(symbol, str) for symbol in result)

    # Tests for new market cap based functionality

    @patch('scripts.get_top50.requests.get')
    @patch('scripts.get_top50._load_cache')
    def test_get_marketcap_top50_success(self, mock_load_cache, mock_get):
        """Test successful fetching of market cap data."""
        mock_load_cache.return_value = None  # No cache
        
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {'symbol': 'btc', 'market_cap': 500000000000},  # CoinGecko returns lowercase
            {'symbol': 'eth', 'market_cap': 200000000000},
            {'symbol': 'usdt', 'market_cap': 50000000000}
        ]
        mock_get.return_value = mock_response

        symbols = get_marketcap_top50(3)

        assert symbols == ['BTC', 'ETH', 'USDT']  # Should be uppercased
        mock_get.assert_called_once()

    @patch('scripts.get_top50.requests.get')
    @patch('scripts.get_top50._load_cache')
    def test_get_marketcap_top50_cache_hit(self, mock_load_cache, mock_get):
        """Test using cached market cap data."""
        mock_load_cache.return_value = {'symbols': ['BTC', 'ETH']}

        symbols = get_marketcap_top50(2)

        assert symbols == ['BTC', 'ETH']
        mock_get.assert_not_called()

    @patch('scripts.get_top50.requests.get')
    @patch('scripts.get_top50._load_cache')
    def test_get_marketcap_top50_api_error_with_cache(self, mock_load_cache, mock_get):
        """Test API error fallback to cache."""
        mock_load_cache.return_value = {'symbols': ['BTC', 'ETH']}
        mock_get.side_effect = Exception("API Error")

        symbols = get_marketcap_top50(2)

        assert symbols == ['BTC', 'ETH']

    @patch('scripts.get_top50.requests.get')
    @patch('scripts.get_top50._load_cache')
    def test_get_marketcap_top50_api_error_no_cache(self, mock_load_cache, mock_get):
        """Test API error with no cache returns empty list."""
        mock_load_cache.return_value = None
        mock_get.side_effect = Exception("API Error")

        symbols = get_marketcap_top50(2)

        assert symbols == []

    @patch('ccxt.okx')
    @patch('scripts.get_top50._load_cache')
    def test_get_okx_swap_symbols_success(self, mock_load_cache, mock_okx_class):
        """Test successful fetching of OKX swap contracts."""
        mock_load_cache.return_value = None  # No cache
        
        mock_exchange = MagicMock()
        mock_okx_class.return_value = mock_exchange

        mock_markets = {
            'BTC/USDT:USDT': {'type': 'swap', 'settle': 'USDT'},
            'ETH/USDT:USDT': {'type': 'swap', 'settle': 'USDT'},
            'BTC/USD:BTC': {'type': 'swap', 'settle': 'BTC'}  # Non-USDT settle
        }
        mock_exchange.load_markets.return_value = mock_markets

        contracts = get_okx_swap_symbols()

        assert contracts == ['BTC-USDT-SWAP', 'ETH-USDT-SWAP']
        assert len(contracts) == 2

    @patch('scripts.get_top50._load_cache')
    def test_get_okx_swap_symbols_cache_hit(self, mock_load_cache):
        """Test using cached OKX contract data."""
        mock_load_cache.return_value = {'contracts': ['BTC-USDT-SWAP', 'ETH-USDT-SWAP']}

        contracts = get_okx_swap_symbols()

        assert contracts == ['BTC-USDT-SWAP', 'ETH-USDT-SWAP']

    def test_filter_top_swap_symbols(self):
        """Test filtering market cap symbols against OKX contracts."""
        marketcap_symbols = ['BTC', 'ETH', 'XRP', 'ADA']
        okx_contracts = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP']

        result = filter_top_swap_symbols(marketcap_symbols, okx_contracts)

        assert result == ['BTC/USDT', 'ETH/USDT']
        assert len(result) == 2

    def test_filter_top_swap_symbols_no_matches(self):
        """Test filtering when no symbols match."""
        marketcap_symbols = ['BTC', 'ETH']
        okx_contracts = ['SOL-USDT-SWAP', 'ADA-USDT-SWAP']

        result = filter_top_swap_symbols(marketcap_symbols, okx_contracts)

        assert result == []

    @patch('scripts.get_top50.get_marketcap_top50')
    @patch('scripts.get_top50.get_okx_swap_symbols')
    @patch('scripts.get_top50.filter_top_swap_symbols')
    def test_get_top50_by_marketcap_success(self, mock_filter, mock_get_okx, mock_get_marketcap):
        """Test successful integration of market cap based selection."""
        mock_get_marketcap.return_value = ['BTC', 'ETH', 'XRP']
        mock_get_okx.return_value = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP']
        mock_filter.return_value = ['BTC/USDT', 'ETH/USDT']

        result = get_top50_by_marketcap()

        assert result == ['BTC/USDT', 'ETH/USDT']
        mock_get_marketcap.assert_called_once_with(50)
        mock_get_okx.assert_called_once()
        mock_filter.assert_called_once()

    @patch('scripts.get_top50.get_marketcap_top50')
    @patch('scripts.get_top50.get_okx_swap_symbols')
    def test_get_top50_by_marketcap_okx_failure(self, mock_get_okx, mock_get_marketcap):
        """Test fallback when OKX contract discovery fails."""
        mock_get_marketcap.return_value = ['BTC', 'ETH']
        mock_get_okx.return_value = []

        result = get_top50_by_marketcap()

        assert result == ['BTC/USDT', 'ETH/USDT']

    def test_load_cache_valid(self):
        """Test loading valid cache data."""
        cache_data = {
            'symbols': ['BTC', 'ETH'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = os.path.join(temp_dir, 'test_cache.json')
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)

            result = _load_cache(cache_file, timedelta(hours=1))

            assert result == cache_data

    def test_load_cache_expired(self):
        """Test loading expired cache data."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        cache_data = {
            'symbols': ['BTC', 'ETH'],
            'timestamp': old_time.isoformat()
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = os.path.join(temp_dir, 'test_cache.json')
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)

            result = _load_cache(cache_file, timedelta(hours=1))

            assert result is None

    def test_load_cache_file_not_exists(self):
        """Test loading cache when file doesn't exist."""
        result = _load_cache('/nonexistent/cache.json', timedelta(hours=1))

        assert result is None

    def test_save_cache(self):
        """Test saving cache data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = os.path.join(temp_dir, 'test_cache.json')

            _save_cache(cache_file, {'test': 'data'})

            assert os.path.exists(cache_file)

            with open(cache_file, 'r') as f:
                data = json.load(f)

            assert data['test'] == 'data'
            assert 'timestamp' in data
