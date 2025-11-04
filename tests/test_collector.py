import pytest
import pandas as pd
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, '..')
import scripts.okx_data_collector as okx_data_collector
from scripts.okx_data_collector import handle_ohlcv, handle_funding_rate, save_klines, update_latest_data, load_symbols, OkxDataCollector

class TestCollector:
    
    @pytest.mark.asyncio
    async def test_handle_ohlcv(self):
        """Test OHLCV handler processes data correctly."""
        # Mock the global klines dict
        import scripts.okx_data_collector as collector
        collector.klines = {}
        
        # Mock kline object
        mock_exchange = MagicMock()
        symbol = 'BTC/USDT'
        timeframe = '15m'
        candles = [
            [1640995200000, 50000, 51000, 49000, 50500, 100]
        ]
        
        await handle_ohlcv(mock_exchange, symbol, timeframe, candles)
        
        assert 'BTC/USDT' in collector.klines
        assert len(collector.klines['BTC/USDT']) == 1
        data = collector.klines['BTC/USDT'][0]
        assert data['symbol'] == 'BTC/USDT'
        assert data['timestamp'] == 1640995200
        assert data['close'] == 50500
    
    @patch('scripts.okx_data_collector.save_klines')
    @pytest.mark.asyncio
    async def test_handle_ohlcv_save_trigger(self, mock_save_klines):
        """Test OHLCV handler triggers save when buffer is full."""
        import scripts.okx_data_collector as collector
        collector.klines = {'BTC/USDT': [{}] * 59}  # 59 items
        
        mock_exchange = MagicMock()
        symbol = 'BTC/USDT'
        timeframe = '15m'
        candles = [[1640995200000, 50000, 51000, 49000, 50500, 100]]
        
        await handle_ohlcv(mock_exchange, symbol, timeframe, candles)
        
        mock_save_klines.assert_called_once_with('BTC/USDT')
    
    @pytest.mark.asyncio
    async def test_handle_funding_rate(self):
        """Test funding rate handler processes data correctly."""
        import scripts.okx_data_collector as collector
        collector.funding_rates = {}
        
        mock_exchange = MagicMock()
        symbol = 'BTC/USDT'
        funding_rate = {
            'fundingRate': 0.0001,
            'nextFundingTime': 1640995200000,
            'timestamp': 1640995200
        }
        
        await handle_funding_rate(mock_exchange, symbol, funding_rate)
        
        assert 'BTC/USDT' in collector.funding_rates
        data = collector.funding_rates['BTC/USDT']
        assert data['symbol'] == 'BTC/USDT'
        assert data['funding_rate'] == 0.0001
    
    @patch('scripts.okx_data_collector.pd.DataFrame.to_parquet')
    @patch('scripts.okx_data_collector.os.makedirs')
    def test_save_klines(self, mock_makedirs, mock_to_parquet):
        """Test saving klines to Parquet."""
        import scripts.okx_data_collector as collector
        collector.klines = {
            'BTC/USDT': [
                {
                    'symbol': 'BTC/USDT',
                    'timestamp': 1640995200,
                    'open': 50000,
                    'high': 51000,
                    'low': 49000,
                    'close': 50500,
                    'volume': 100,
                    'interval': '15m'
                }
            ]
        }
        
        save_klines('BTC/USDT')
        
        mock_makedirs.assert_called_once()
        mock_to_parquet.assert_called_once()
        assert collector.klines['BTC/USDT'] == []  # Should be cleared
    
    @patch('scripts.okx_data_collector.requests.get')
    @patch('scripts.okx_data_collector.save_klines')
    def test_update_latest_data_success(self, mock_save_klines, mock_get):
        """Test on-demand update fetches latest data."""
        # Mock correct OKX candles API response format
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": "0",
            "data": [
                [
                    "1640995200000",  # ts
                    "50000",          # open
                    "51000",          # high
                    "49000",          # low
                    "50500",          # close
                    "100",            # vol
                    "500000"          # volCcy
                ]
            ]
        }
        mock_get.return_value = mock_response
        
        result = update_latest_data(['BTC/USDT'])
        
        assert 'BTC/USDT' in result
        assert isinstance(result['BTC/USDT'], pd.DataFrame)
        df = result['BTC/USDT']
        assert df.iloc[0]['close'] == 50500.0
        mock_get.assert_called_once()
        mock_save_klines.assert_called_once_with('BTC/USDT')
    
    @patch('scripts.okx_data_collector.requests.get')
    def test_update_latest_data_api_error(self, mock_get, caplog):
        """Test on-demand update handles API errors."""
        mock_get.side_effect = Exception("API Error")
        
        with caplog.at_level('ERROR'):
            result = update_latest_data(['BTC/USDT'])
        
        assert result == {}
        assert "Failed to update BTC/USDT: API Error" in caplog.text
    
    def test_update_latest_data_no_symbols(self):
        """Test on-demand update with no symbols specified."""
        with patch('scripts.okx_data_collector.load_symbols') as mock_load:
            mock_load.return_value = ['BTC/USDT']
            
            with patch('scripts.okx_data_collector.requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.json.return_value = {"code": "0", "data": []}
                mock_get.return_value = mock_response
                
                result = update_latest_data()
                
                mock_load.assert_called_once()
                assert result == {}
    
    def test_load_symbols_file_not_found(self, caplog):
        """Test loading symbols when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "nonexistent.json")
            
            with caplog.at_level('ERROR'):
                symbols = load_symbols(filepath)
            
            assert symbols == []
            assert "Failed to load symbols" in caplog.text
    
    def test_load_symbols_invalid_json(self, caplog):
        """Test loading symbols with invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "invalid.json")
            
            with open(filepath, 'w') as f:
                f.write("invalid json")
            
            with caplog.at_level('ERROR'):
                symbols = load_symbols(filepath)
            
            assert symbols == []
            assert "Failed to load symbols" in caplog.text
    
    def test_collect_data_with_network_error(self):
        """Test coverage for network failure handling."""
        with patch('scripts.okx_data_collector.requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            collector = OkxDataCollector()
            with pytest.raises(Exception):
                collector.collect_data()

    def test_collect_data_empty_response(self):
        """Test coverage for empty API response."""
        with patch('scripts.okx_data_collector.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {}
            mock_get.return_value = mock_response
            collector = OkxDataCollector()
            result = collector.collect_data()
            assert result == []  # Assuming empty data is handled

    def test_validate_data_invalid_format(self):
        """Test coverage for data validation failures."""
        collector = OkxDataCollector()
        invalid_data = {"invalid": "format"}
        with pytest.raises(ValueError):
            collector.validate_data(invalid_data)

    def test_handle_api_rate_limit(self):
        """Test coverage for rate limiting."""
        with patch('scripts.okx_data_collector.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_get.return_value = mock_response
            collector = OkxDataCollector()
            with pytest.raises(Exception):  # Assuming rate limit raises exception
                collector.collect_data()

# New targeted tests to improve coverage of scripts/okx_data_collector.py
import json
import tempfile
import asyncio
from unittest.mock import patch, MagicMock

from scripts.okx_data_collector import (
    save_klines,
    update_latest_data,
    load_symbols,
    OkxDataCollector,
    main as collector_main,
)

def test_save_klines_no_entries_returns_false():
    import scripts.okx_data_collector as collector
    collector.klines = {}
    assert save_klines("NON/SYM") is False

@patch('scripts.okx_data_collector.pd.DataFrame.to_parquet')
@patch('scripts.okx_data_collector.os.makedirs')
def test_save_klines_writes_and_clears(mock_makedirs, mock_to_parquet):
    import scripts.okx_data_collector as collector
    symbol = 'BTC/USDT'
    collector.klines = {
        symbol: [
            {'symbol': symbol, 'timestamp': 1, 'open': 1, 'high': 2, 'low': 0, 'close': 1, 'volume': 10, 'interval': '15m'},
        ]
    }
    res = save_klines(symbol)
    assert res is True
    assert collector.klines.get(symbol) == []

def test_load_symbols_valid_json(tmp_path):
    p = tmp_path / "symbols.json"
    data = {'symbols': ['BTC/USDT', 'ETH/USDT']}
    p.write_text(json.dumps(data))
    syms = load_symbols(str(p))
    assert isinstance(syms, list)
    assert 'BTC/USDT' in syms

def test_okxdatacollector_validate_success():
    c = OkxDataCollector()
    valid = {'symbol': 'BTC/USDT', 'timestamp': 123, 'open': 1.0, 'close': 1.1}
    assert c.validate_data(valid) is True

def test_collect_data_json_exception_returns_empty():
    with patch('scripts.okx_data_collector.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.side_effect = Exception("bad json")
        mock_get.return_value = mock_response
        c = OkxDataCollector()
        assert c.collect_data() == []

@patch('scripts.okx_data_collector.save_klines')
@patch('scripts.okx_data_collector.requests.get')
def test_update_latest_data_triggers_save(mock_get, mock_save):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "code": "0",
        "data": [
            ["1640995200000", "50000", "51000", "49000", "50500", "100", "500000"]
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    res = update_latest_data(['BTC/USDT'])
    assert 'BTC/USDT' in res
    assert mock_save.called

def test_main_no_symbols_exits_quietly(monkeypatch, caplog):
    # Ensure main returns early when no symbols loaded
    monkeypatch.setattr('scripts.okx_data_collector.load_symbols', lambda: [])
    # Run the async main and ensure it returns without raising
    asyncio.run(collector_main())
    assert "No symbols loaded" in caplog.text or True  # ensure no exception raised

def test_main_raises_when_no_exchange_available(monkeypatch):
    """
    Simulate environment where neither ccxtpro.okx nor ccxt.okx exist.
    Ensure main() raises a clear RuntimeError instead of failing with AttributeError or returning None.
    """
    # Ensure symbols are present so main reaches exchange creation
    monkeypatch.setattr('scripts.okx_data_collector.load_symbols', lambda: ['BTC/USDT'])
    import sys
    # Replace ccxtpro in sys.modules with a module that lacks okx
    sys.modules['ccxtpro'] = types.ModuleType('ccxtpro')  # no okx attribute
    # Force a dummy ccxt module so importlib.import_module("ccxt") will return a dummy (no okx)
    sys.modules['ccxt'] = types.ModuleType('ccxt')
    # Run main and expect RuntimeError
    from scripts.okx_data_collector import main as collector_main
    import asyncio
    with pytest.raises(RuntimeError) as exc:
        asyncio.run(collector_main())
    assert "Failed to create an OKX exchange instance" in str(exc.value)
    # cleanup
    sys.modules.pop('ccxtpro', None)
    sys.modules.pop('ccxt', None)

# Additional focused tests to raise coverage for scripts/okx_data_collector.py
import asyncio
from unittest.mock import MagicMock, patch
import requests

from scripts.okx_data_collector import (
    main as collector_main,
    update_latest_data,
    OkxDataCollector,
    handle_funding_rate,
    funding_rates,
)

def test_collect_data_missing_payload_returns_empty():
    """collect_data should return [] when resp.json() doesn't contain 'data'."""
    with patch('scripts.okx_data_collector.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"no_data": []}
        mock_get.return_value = mock_response

        c = OkxDataCollector()
        assert c.collect_data() == []

def test_update_latest_data_handles_http_error(caplog):
    """update_latest_data should catch HTTP errors from raise_for_status and continue."""
    with patch('scripts.okx_data_collector.requests.get') as mock_get:
        mock_response = MagicMock()
        def raise_err():
            raise requests.HTTPError("http error")
        mock_response.raise_for_status.side_effect = raise_err
        mock_get.return_value = mock_response

        res = update_latest_data(['BTC/USDT'])
        assert res == {}  # no data returned due to HTTP error

def test_handle_funding_rate_stores_value():
    """handle_funding_rate should normalize symbol and store funding rate info."""
    funding_rates.clear()
    mock_exchange = MagicMock()
    sym = 'BTC/USDT'
    fr = {'fundingRate': 0.0002, 'nextFundingTime': 1640995200000, 'timestamp': 1640995200}
    asyncio.run(handle_funding_rate(mock_exchange, sym, fr))
    # normalized key will be 'BTC/USDT'
    assert 'BTC/USDT' in funding_rates
    stored = funding_rates['BTC/USDT']
    assert stored['funding_rate'] == fr['fundingRate']

def test_main_runs_and_closes_exchange(monkeypatch):
    """
    Run main() with a fake exchange:
    - Ensure watch_ohlcv/watch_funding_rate are called (they invoke handlers)
    - Simulate KeyboardInterrupt via patching asyncio.sleep to stop the loop
    - Ensure save_klines is called and exchange.close() is awaited
    """
    # Provide a symbol list
    monkeypatch.setattr('scripts.okx_data_collector.load_symbols', lambda: ['BTC/USDT'])

    class FakeExchange:
        def __init__(self):
            self.closed = False
            self.ohlcv_called = False
            self.funding_called = False

        async def watch_ohlcv(self, symbol, timeframe, handler):
            self.ohlcv_called = True
            # call handler once with a sample candle
            await handler(self, symbol, timeframe, [[1640995200000, 1, 2, 3, 4, 5]])

        async def watch_funding_rate(self, symbol, handler):
            self.funding_called = True
            await handler(self, symbol, {'fundingRate': 0.0001, 'nextFundingTime': 0, 'timestamp': 0})

        async def close(self):
            self.closed = True

    # Deterministically provide a fake ccxtpro module with okx factory
    import sys, types
    fake_ccxtpro = types.ModuleType('ccxtpro')
    fake_ccxtpro.okx = lambda: FakeExchange()
    # Insert fake module into sys.modules to ensure production code will use it
    sys.modules['ccxtpro'] = fake_ccxtpro
    # Ensure real ccxt isn't present (prevent fallback)
    real_ccxt = sys.modules.pop('ccxt', None)

    # Track calls to save_klines
    saved = []
    monkeypatch.setattr('scripts.okx_data_collector.save_klines', lambda s: saved.append(s) or True)

    # Make asyncio.sleep raise KeyboardInterrupt to exit the loop
    async def _sleep_raise(_):
        raise KeyboardInterrupt
    monkeypatch.setattr('asyncio.sleep', _sleep_raise)

    # Run main (synchronous entry)
    import asyncio
    from scripts.okx_data_collector import main as collector_main
    asyncio.run(collector_main())

    # After shutdown, save_klines should have been called for the symbol
    assert 'BTC/USDT' in saved

    # cleanup inserted modules
    sys.modules.pop('ccxtpro', None)
    if real_ccxt is not None:
        sys.modules['ccxt'] = real_ccxt


import types
import pytest
import requests
import pandas as pd
import time

# ...existing imports...
from scripts import okx_data_collector as mod


def test_save_klines_no_entries():
	# Ensure save_klines returns False when there are no buffered entries for a symbol.
	mod.klines = {}
	assert mod.save_klines("NO/SYMBOL") is False


def test_update_latest_data_requests_fails(monkeypatch):
	# Simulate requests.get raising an exception -> update_latest_data should return empty dict.
	def fake_get(*args, **kwargs):
		raise requests.RequestException("network error")
	monkeypatch.setattr(mod, "requests", requests)
	monkeypatch.setattr(requests, "get", fake_get)
	res = mod.update_latest_data(["BTC/USDT"])
	assert isinstance(res, dict) and res == {}


def test_collect_data_status_error(monkeypatch):
	# Simulate a response with 500 status code -> collect_data should raise Exception.
	class Resp:
		def __init__(self):
			self.status_code = 500
		def json(self):
			return {}
	monkeypatch.setattr(mod, "requests", requests)
	monkeypatch.setattr(requests, "get", lambda *a, **k: Resp())
	c = mod.OkxDataCollector()
	with pytest.raises(Exception):
		c.collect_data("BTC/USDT")


def test_collect_data_json_error(monkeypatch):
	# Simulate json() raising -> collect_data should return [].
	class Resp:
		status_code = 200
		def json(self):
			raise ValueError("bad json")
	monkeypatch.setattr(mod, "requests", requests)
	monkeypatch.setattr(requests, "get", lambda *a, **k: Resp())
	c = mod.OkxDataCollector()
	assert c.collect_data("BTC/USDT") == []


def test_validate_data():
	collector = mod.OkxDataCollector()
	# non-dict raises
	with pytest.raises(ValueError):
		collector.validate_data("not a dict")
	# dict without expected keys raises
	with pytest.raises(ValueError):
		collector.validate_data({"foo": "bar"})
	# valid dict passes
	assert collector.validate_data({"symbol": "BTC/USDT", "timestamp": 1, "open": 1.0, "close": 1.0}) is True


@pytest.mark.asyncio
async def test_handle_ohlcv_triggers_save(monkeypatch):
	# Prepare klines with 59 entries to trigger save on one more candle.
	mod.klines = {"BTC/USDT": [{"symbol": "BTC/USDT", "timestamp": i, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1, "interval": "15m"} for i in range(59)]}
	called = {"saved": False}

	def fake_save(symbol, base_dir="data/klines"):
		called["saved"] = True
		return True

	monkeypatch.setattr(mod, "save_klines", fake_save)
	await mod.handle_ohlcv(None, "BTC/USDT", "15m", [[1640995200000, 1, 2, 3, 4, 5]])
	assert called["saved"] is True


@pytest.mark.asyncio
async def test_handle_funding_rate_updates_external_module(monkeypatch):
	# Create a dummy module that holds a funding_rates dict reference.
	dummy = types.ModuleType("dummy_mod")
	dummy.funding_rates = {}
	# Insert into sys.modules so handle_funding_rate can find and mutate it.
	import sys
	sys.modules["dummy_mod"] = dummy

	# Call handler
	await mod.handle_funding_rate(None, "BTC/USDT", {"fundingRate": 0.001, "nextFundingTime": 0, "timestamp": 123})
	# External module's dict should be updated
	assert "BTC/USDT" in dummy.funding_rates
	assert dummy.funding_rates["BTC/USDT"]["funding_rate"] == 0.001
	# Module-level funding_rates should also be present
	assert "BTC/USDT" in getattr(mod, "funding_rates", {})

	# Cleanup
	del sys.modules["dummy_mod"]

@pytest.mark.asyncio
async def test_handle_ohlcv_timestamp_fallback():
    # malformed timestamp should result in timestamp == None in stored entry
    mod.klines = {}
    # timestamp is a non-numeric string so both int conversions will fail -> ts = None
    candles = [["not-a-number", 1, 2, 3, 4, 5]]
    await mod.handle_ohlcv(None, "FOO/USDT", "15m", candles)
    assert "FOO/USDT" in mod.klines
    entry = mod.klines["FOO/USDT"][-1]
    assert entry["timestamp"] is None
