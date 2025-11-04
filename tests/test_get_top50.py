import pytest
import json
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.get_top50 import get_okx_funding_top50, save_symbols, load_symbols

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

if __name__ == "__main__":
    pytest.main([__file__])
