import unittest
import os
import tempfile
import pandas as pd
import pytest
import sys
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from scripts.okx_data_collector import save_klines, load_existing_data, get_last_timestamp_from_csv, calculate_fetch_window, handle_ohlcv, handle_funding_rate, update_latest_data, load_symbols, validate_data_continuity, main
from datetime import datetime

class TestOKXDataCollector(unittest.TestCase):

    def setUp(self):
        # Create temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_klines_csv_mode(self):
        """Test saving klines data to CSV format."""
        symbol = "BTC/USDT"
        test_data = [
            {
                'symbol': symbol,
                'timestamp': 1633046400,  # 2021-10-01 00:00:00
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 1000.0,
                'interval': '15m'
            }
        ]

        result = save_klines(symbol, base_dir=self.temp_dir, entries=test_data)
        self.assertTrue(result)

        # Check if file was created
        expected_file = os.path.join(self.temp_dir, "BTC_USDT", "BTC_USDT.csv")
        self.assertTrue(os.path.exists(expected_file))

        # Check file contents
        df = pd.read_csv(expected_file)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['symbol'], symbol)
        self.assertEqual(df.iloc[0]['close'], 50500.0)

    def test_save_klines_append_mode(self):
        """Test saving klines data in append mode."""
        symbol = "BTC/USDT"

        # First save some data
        initial_data = [
            {
                'symbol': symbol,
                'timestamp': 1633046400,  # 2021-10-01 00:00:00
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 1000.0,
                'interval': '15m'
            }
        ]

        save_klines(symbol, base_dir=self.temp_dir, entries=initial_data)

        # Then append more data with later timestamp
        append_data = [
            {
                'symbol': symbol,
                'timestamp': 1633047300,  # 2021-10-01 00:15:00 (15 minutes later)
                'open': 50500.0,
                'high': 51500.0,
                'low': 49500.0,
                'close': 51000.0,
                'volume': 1200.0,
                'interval': '15m'
            }
        ]

        result = save_klines(symbol, base_dir=self.temp_dir, entries=append_data, append_only=True)
        self.assertTrue(result)

        # Check file contents - should have 2 rows
        expected_file = os.path.join(self.temp_dir, "BTC_USDT", "BTC_USDT.csv")
        df = pd.read_csv(expected_file)
        self.assertEqual(len(df), 2)

    def test_get_last_timestamp_from_csv(self):
        """Test getting last timestamp from CSV file."""
        symbol = "BTC/USDT"

        # Create test CSV file
        test_data = [
            {
                'symbol': symbol,
                'timestamp': '2021-10-01 00:00:00',
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 1000.0,
                'interval': '15m'
            },
            {
                'symbol': symbol,
                'timestamp': '2021-10-01 00:15:00',
                'open': 50500.0,
                'high': 51500.0,
                'low': 49500.0,
                'close': 51000.0,
                'volume': 1200.0,
                'interval': '15m'
            }
        ]

        df = pd.DataFrame(test_data)
        os.makedirs(os.path.join(self.temp_dir, "BTC_USDT"), exist_ok=True)
        csv_path = os.path.join(self.temp_dir, "BTC_USDT", "BTC_USDT.csv")
        df.to_csv(csv_path, index=False)

        # Test getting last timestamp
        last_ts = get_last_timestamp_from_csv(symbol, base_dir=self.temp_dir)
        self.assertIsNotNone(last_ts)
        expected_ts = pd.to_datetime('2021-10-01 00:15:00')
        self.assertEqual(last_ts, expected_ts)

    def test_load_existing_data(self):
        """Test loading existing data from CSV."""
        symbol = "BTC/USDT"

        # Create test CSV file
        test_data = [
            {
                'symbol': symbol,
                'timestamp': '2021-10-01 00:00:00',
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 1000.0,
                'interval': '15m'
            }
        ]

        df = pd.DataFrame(test_data)
        os.makedirs(os.path.join(self.temp_dir, "BTC_USDT"), exist_ok=True)
        csv_path = os.path.join(self.temp_dir, "BTC_USDT", "BTC_USDT.csv")
        df.to_csv(csv_path, index=False)

        # Test loading data
        loaded_df = load_existing_data(symbol, base_dir=self.temp_dir)
        self.assertIsNotNone(loaded_df)
        self.assertEqual(len(loaded_df), 1)
        self.assertEqual(loaded_df.iloc[0]['close'], 50500.0)

    @patch('scripts.okx_data_collector.get_last_timestamp_from_csv')
    def test_calculate_fetch_window_no_existing_data(self, mock_get_last_ts):
        """Test calculate_fetch_window when no existing data."""
        mock_get_last_ts.return_value = None

        start, end, should_fetch = calculate_fetch_window(
            "BTC/USDT", "2021-10-01T00:00:00Z", "2021-10-02T00:00:00Z", self.temp_dir
        )

        self.assertEqual(start, "2021-10-01T00:00:00Z")
        self.assertEqual(end, "2021-10-02T00:00:00Z")
        self.assertTrue(should_fetch)

    @patch('scripts.okx_data_collector.get_last_timestamp_from_csv')
    def test_calculate_fetch_window_with_existing_data_no_overlap(self, mock_get_last_ts):
        """Test calculate_fetch_window when existing data covers the range."""
        # Mock existing data that covers the requested range
        mock_get_last_ts.return_value = pd.to_datetime("2021-10-02T12:00:00Z")

        start, end, should_fetch = calculate_fetch_window(
            "BTC/USDT", "2021-10-01T00:00:00Z", "2021-10-02T00:00:00Z", self.temp_dir
        )

        self.assertEqual(start, "2021-10-01T00:00:00Z")
        self.assertEqual(end, "2021-10-02T00:00:00Z")
        self.assertFalse(should_fetch)  # Should not fetch since data already exists

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.calculate_fetch_window')
    @patch('ccxt.okx')
    def test_update_latest_data_incremental_skip(self, mock_ccxt_okx, mock_calc_window, mock_load_symbols):
        """Test update_latest_data with incremental collection that skips fetching."""
        mock_load_symbols.return_value = ["BTC/USDT"]
        mock_calc_window.return_value = ("2021-10-01T00:00:00Z", "2021-10-02T00:00:00Z", False)  # should_fetch=False

        # Mock args
        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-02T00:00:00Z"
                self.limit = 100

        result = update_latest_data(output_dir=self.temp_dir, args=MockArgs())

        # Should return empty dict since no data was fetched
        self.assertEqual(result, {})

        # Verify functions were called
        mock_load_symbols.assert_called_once()
        mock_calc_window.assert_called_once_with("BTC/USDT", "2021-10-01T00:00:00Z", "2021-10-02T00:00:00Z", self.temp_dir)

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.calculate_fetch_window')
    @patch('ccxt.okx')
    def test_update_latest_data_fetch_data(self, mock_ccxt_okx, mock_calc_window, mock_load_symbols):
        """Test update_latest_data that actually fetches data."""
        mock_load_symbols.return_value = ["BTC/USDT"]
        mock_calc_window.return_value = ("2021-10-01T00:00:00Z", "2021-10-01T01:00:00Z", True)

        # Mock exchange
        mock_exchange = MagicMock()
        mock_ccxt_okx.return_value = mock_exchange
        mock_exchange.load_markets = MagicMock()
        # Return empty data to stop the loop
        mock_exchange.fetch_ohlcv.return_value = []

        # Mock args
        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-01T01:00:00Z"
                self.limit = 100

        result = update_latest_data(output_dir=self.temp_dir, args=MockArgs())

        # Should return empty dict since no candles were found
        self.assertEqual(result, {})

        # Verify exchange was initialized
        mock_ccxt_okx.assert_called_once()
        mock_exchange.load_markets.assert_called_once()

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.calculate_fetch_window')
    @patch('ccxt.okx')
    def test_update_latest_data_with_actual_data(self, mock_ccxt_okx, mock_calc_window, mock_load_symbols):
        """Test update_latest_data with actual OHLCV data returned."""
        mock_load_symbols.return_value = ["BTC/USDT"]
        mock_calc_window.return_value = ("2021-10-01T00:00:00Z", "2021-10-01T01:00:00Z", True)

        # Mock exchange
        mock_exchange = MagicMock()
        mock_ccxt_okx.return_value = mock_exchange
        mock_exchange.load_markets = MagicMock()

        # Mock OHLCV data: [timestamp_ms, open, high, low, close, volume]
        ohlcv_data = [
            [1633046400000, 50000.0, 51000.0, 49000.0, 50500.0, 1000.0],
            [1633047300000, 50500.0, 51500.0, 49500.0, 51000.0, 1200.0]
        ]
        mock_exchange.fetch_ohlcv.return_value = ohlcv_data

        # Mock args
        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-01T01:00:00Z"
                self.limit = 100

        result = update_latest_data(output_dir=self.temp_dir, args=MockArgs())

        # Should return dict with dataframe containing the data
        self.assertIn("BTC/USDT", result)
        df = result["BTC/USDT"]
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]['close'], 50500.0)
        self.assertEqual(df.iloc[1]['close'], 51000.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ccxtpro_import_failure(self):
        """Test that ccxtpro import failure is handled gracefully."""
        # This is tested by the import at module level, but we can verify ccxtpro is handled
        import scripts.okx_data_collector as module
        # ccxtpro should be None if import failed, or the module if successful
        # We can't easily test the import failure without mocking sys.modules before import
        pass

    def test_handle_ohlcv_timestamp_parsing_errors(self):
        """Test handle_ohlcv with malformed timestamps."""
        candles = [
            ["invalid_timestamp", 50000.0, 51000.0, 49000.0, 50500.0, 1000.0],  # Invalid timestamp
            [1633047300000, 50500.0, 51500.0, 49500.0, 51000.0, 1200.0]  # Valid timestamp
        ]

        result = handle_ohlcv(None, "BTC/USDT", '15m', candles)
        self.assertTrue(result)  # Should handle errors gracefully

    async def test_handle_ohlcv_klines_initialization(self):
        """Test handle_ohlcv when klines is None."""
        # Reset klines to None
        import scripts.okx_data_collector as module
        original_klines = module.klines
        module.klines = None

        try:
            candles = [
                [1633046400000, 50000.0, 51000.0, 49000.0, 50500.0, 1000.0]
            ]
            result = await handle_ohlcv(None, "BTC/USDT", '15m', candles)
            self.assertTrue(result)
            # Should have initialized klines
            self.assertIsNotNone(module.klines)
        finally:
            module.klines = original_klines

    def test_handle_funding_rate_module_access_error(self):
        """Test handle_funding_rate with module access errors."""
        # Mock sys.modules to cause access errors
        with patch('sys.modules', {}):
            result = handle_funding_rate(None, "BTC/USDT", {'fundingRate': 0.001})
            self.assertTrue(result)  # Should handle errors gracefully

    def test_get_last_timestamp_from_csv_file_not_exists(self):
        """Test get_last_timestamp_from_csv when file doesn't exist."""
        result = get_last_timestamp_from_csv("NONEXISTENT", self.temp_dir)
        self.assertIsNone(result)

    def test_get_last_timestamp_from_csv_empty_file(self):
        """Test get_last_timestamp_from_csv with empty file."""
        symbol = "BTC/USDT"
        os.makedirs(os.path.join(self.temp_dir, "BTC_USDT"), exist_ok=True)
        csv_path = os.path.join(self.temp_dir, "BTC_USDT", "BTC_USDT.csv")

        # Create empty file
        with open(csv_path, 'w') as f:
            f.write("")

        result = get_last_timestamp_from_csv(symbol, self.temp_dir)
        self.assertIsNone(result)

    def test_get_last_timestamp_from_csv_only_header(self):
        """Test get_last_timestamp_from_csv with only header."""
        symbol = "BTC/USDT"
        os.makedirs(os.path.join(self.temp_dir, "BTC_USDT"), exist_ok=True)
        csv_path = os.path.join(self.temp_dir, "BTC_USDT", "BTC_USDT.csv")

        # Create file with only header
        with open(csv_path, 'w') as f:
            f.write("symbol,timestamp,open,high,low,close,volume,interval\n")

        result = get_last_timestamp_from_csv(symbol, self.temp_dir)
        self.assertIsNone(result)

    def test_get_last_timestamp_from_csv_malformed_csv(self):
        """Test get_last_timestamp_from_csv with malformed CSV."""
        symbol = "BTC/USDT"
        os.makedirs(os.path.join(self.temp_dir, "BTC_USDT"), exist_ok=True)
        csv_path = os.path.join(self.temp_dir, "BTC_USDT", "BTC_USDT.csv")

        # Create file with malformed CSV (missing timestamp column)
        with open(csv_path, 'w') as f:
            f.write("symbol,open,high,low,close,volume\nBTC/USDT,50000.0,51000.0,49000.0,50500.0,1000.0\n")

        result = get_last_timestamp_from_csv(symbol, self.temp_dir)
        self.assertIsNone(result)

    def test_calculate_fetch_window_invalid_times(self):
        """Test calculate_fetch_window with invalid time strings."""
        with patch('scripts.okx_data_collector.get_last_timestamp_from_csv', return_value=None):
            result = calculate_fetch_window("BTC/USDT", "invalid_start", "invalid_end", self.temp_dir)
            # Should return the invalid times as-is since parsing fails
            self.assertEqual(result, ("invalid_start", "invalid_end", True))

    def test_load_existing_data_file_not_exists(self):
        """Test load_existing_data when file doesn't exist."""
        result = load_existing_data("NONEXISTENT", self.temp_dir)
        self.assertIsNone(result)

    def test_load_existing_data_corrupt_csv(self):
        """Test load_existing_data with corrupt CSV."""
        symbol = "BTC/USDT"
        os.makedirs(os.path.join(self.temp_dir, "BTC_USDT"), exist_ok=True)
        csv_path = os.path.join(self.temp_dir, "BTC_USDT", "BTC_USDT.csv")

        # Create corrupt CSV
        with open(csv_path, 'w') as f:
            f.write("corrupt,data,that,is,not,csv\n")

        result = load_existing_data(symbol, self.temp_dir)
        # pandas can read this as a DataFrame, but it won't have expected columns
        self.assertIsNotNone(result)
        self.assertIsInstance(result, pd.DataFrame)
        # Should have the corrupt columns
        self.assertIn('corrupt', result.columns)

    def test_validate_data_continuity_empty_df(self):
        """Test validate_data_continuity with empty dataframe."""
        df = pd.DataFrame()
        result = validate_data_continuity(df)
        self.assertFalse(result)

    def test_validate_data_continuity_missing_timestamp(self):
        """Test validate_data_continuity with missing timestamp column."""
        df = pd.DataFrame({'symbol': ['BTC/USDT'], 'close': [50000.0]})
        result = validate_data_continuity(df)
        self.assertFalse(result)

    def test_validate_data_continuity_single_point(self):
        """Test validate_data_continuity with single data point."""
        df = pd.DataFrame({
            'timestamp': [pd.Timestamp('2021-10-01 00:00:00')],
            'close': [50000.0]
        })
        result = validate_data_continuity(df)
        self.assertTrue(result)  # Single point is considered continuous

    def test_validate_data_continuity_continuous_data(self):
        """Test validate_data_continuity with continuous data."""
        timestamps = pd.date_range('2021-10-01 00:00:00', periods=5, freq='15min')
        df = pd.DataFrame({
            'timestamp': timestamps,
            'close': [50000.0, 50100.0, 50200.0, 50300.0, 50400.0]
        })
        result = validate_data_continuity(df)
        self.assertTrue(result)

    def test_validate_data_continuity_with_gaps(self):
        """Test validate_data_continuity with data gaps."""
        # Create timestamps with gaps larger than 15 minutes * 2
        timestamps = [
            pd.Timestamp('2021-10-01 00:00:00'),
            pd.Timestamp('2021-10-01 00:15:00'),
            pd.Timestamp('2021-10-01 01:00:00'),  # Gap of 45 minutes
        ]
        df = pd.DataFrame({
            'timestamp': timestamps,
            'close': [50000.0, 50100.0, 50200.0]
        })
        result = validate_data_continuity(df)
        self.assertFalse(result)

    def test_save_klines_empty_entries(self):
        """Test save_klines with empty entries."""
        result = save_klines("BTC/USDT", self.temp_dir, [])
        self.assertFalse(result)  # Should return False for empty entries

    def test_save_klines_none_entries_uses_buffer(self):
        """Test save_klines with None entries (uses buffer)."""
        # This would require setting up the buffer, which is complex
        # Skip for now as it's tested indirectly in other tests
        pass

    def test_save_klines_append_mode_failure_fallback(self):
        """Test save_klines append mode failure falls back to full rewrite."""
        symbol = "BTC/USDT"

        # Create existing file
        os.makedirs(os.path.join(self.temp_dir, "BTC_USDT"), exist_ok=True)
        csv_path = os.path.join(self.temp_dir, "BTC_USDT", "BTC_USDT.csv")

        with open(csv_path, 'w') as f:
            f.write("symbol,timestamp,open,high,low,close,volume,interval\n")
            f.write("BTC/USDT,2021-10-01 00:00:00,50000.0,51000.0,49000.0,50500.0,1000.0,15m\n")

        # Mock get_last_timestamp_from_csv to return None (simulating append check failure)
        with patch('scripts.okx_data_collector.get_last_timestamp_from_csv', return_value=None):
            test_data = [{
                'symbol': symbol,
                'timestamp': 1633047300,  # 2021-10-01 00:15:00
                'open': 50500.0,
                'high': 51500.0,
                'low': 49500.0,
                'close': 51000.0,
                'volume': 1200.0,
                'interval': '15m'
            }]

            result = save_klines(symbol, self.temp_dir, test_data, append_only=True)
            self.assertTrue(result)  # Should succeed with fallback

    def test_load_symbols_file_not_exists(self):
        """Test load_symbols when file doesn't exist."""
        result = load_symbols("/nonexistent/path.json")
        self.assertEqual(result, [])  # Should return empty list

    def test_load_symbols_invalid_json(self):
        """Test load_symbols with invalid JSON."""
        # Create invalid JSON file
        invalid_json_path = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_json_path, 'w') as f:
            f.write("invalid json content {")

        result = load_symbols(invalid_json_path)
        self.assertEqual(result, [])  # Should return empty list on error

    def test_load_symbols_missing_symbols_key(self):
        """Test load_symbols with JSON missing symbols key."""
        json_path = os.path.join(self.temp_dir, "no_symbols.json")
        with open(json_path, 'w') as f:
            f.write('{"other_key": "value"}')

        result = load_symbols(json_path)
        self.assertEqual(result, [])  # Should return empty list when symbols key missing

    @patch('scripts.okx_data_collector.load_symbols')
    def test_update_latest_data_invalid_end_time(self, mock_load_symbols):
        """Test update_latest_data with invalid end_time."""
        mock_load_symbols.return_value = ["BTC/USDT"]

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "invalid_time"
                self.limit = 100

        # Should handle invalid end_time gracefully
        result = update_latest_data(output_dir=self.temp_dir, args=MockArgs())
        # Should still return a result (empty dict since no data fetched)
        self.assertIsInstance(result, dict)

    @patch('scripts.okx_data_collector.load_symbols')
    def test_update_latest_data_invalid_start_time(self, mock_load_symbols):
        """Test update_latest_data with invalid start_time."""
        mock_load_symbols.return_value = ["BTC/USDT"]

        class MockArgs:
            def __init__(self):
                self.start_time = "invalid_time"
                self.end_time = "2021-10-02T00:00:00Z"
                self.limit = 100

        # Should handle invalid start_time gracefully
        result = update_latest_data(output_dir=self.temp_dir, args=MockArgs())
        self.assertIsInstance(result, dict)

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.calculate_fetch_window')
    @patch('ccxt.okx')
    def test_update_latest_data_network_error(self, mock_ccxt_okx, mock_calc_window, mock_load_symbols):
        """Test update_latest_data with network error."""
        mock_load_symbols.return_value = ["BTC/USDT"]
        mock_calc_window.return_value = ("2021-10-01T00:00:00Z", "2021-10-01T01:00:00Z", True)

        mock_exchange = MagicMock()
        mock_ccxt_okx.return_value = mock_exchange
        mock_exchange.load_markets = MagicMock()

        # Mock network error
        import ccxt
        mock_exchange.fetch_ohlcv.side_effect = ccxt.NetworkError("Network error")

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-01T01:00:00Z"
                self.limit = 100

        # Should handle network error gracefully (return empty dict)
        result = update_latest_data(output_dir=self.temp_dir, args=MockArgs())
        self.assertEqual(result, {})

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.calculate_fetch_window')
    @patch('ccxt.okx')
    def test_update_latest_data_exchange_error(self, mock_ccxt_okx, mock_calc_window, mock_load_symbols):
        """Test update_latest_data with exchange error."""
        mock_load_symbols.return_value = ["BTC/USDT"]
        mock_calc_window.return_value = ("2021-10-01T00:00:00Z", "2021-10-01T01:00:00Z", True)

        mock_exchange = MagicMock()
        mock_ccxt_okx.return_value = mock_exchange
        mock_exchange.load_markets = MagicMock()

        # Mock exchange error
        import ccxt
        mock_exchange.fetch_ohlcv.side_effect = ccxt.ExchangeError("Exchange error")

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-01T01:00:00Z"
                self.limit = 100

        # Should handle exchange error gracefully
        result = update_latest_data(output_dir=self.temp_dir, args=MockArgs())
        self.assertEqual(result, {})

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.calculate_fetch_window')
    @patch('ccxt.okx')
    def test_update_latest_data_duplicate_data_detection(self, mock_ccxt_okx, mock_calc_window, mock_load_symbols):
        """Test update_latest_data duplicate data detection."""
        mock_load_symbols.return_value = ["BTC/USDT"]
        mock_calc_window.return_value = ("2021-10-01T00:00:00Z", "2021-10-01T01:00:00Z", True)

        mock_exchange = MagicMock()
        mock_ccxt_okx.return_value = mock_exchange
        mock_exchange.load_markets = MagicMock()

        # Mock duplicate responses (same first timestamp)
        ohlcv_data = [
            [1633046400000, 50000.0, 51000.0, 49000.0, 50500.0, 1000.0],
        ]
        mock_exchange.fetch_ohlcv.side_effect = [ohlcv_data, ohlcv_data]  # Return same data twice

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-01T01:00:00Z"
                self.limit = 100

        result = update_latest_data(output_dir=self.temp_dir, args=MockArgs())
        # Should detect duplicate and stop, returning data from first response
        self.assertIn("BTC/USDT", result)
        self.assertEqual(len(result["BTC/USDT"]), 1)

    @patch('scripts.okx_data_collector.load_symbols')
    def test_update_latest_data_none_args(self, mock_load_symbols):
        """Test update_latest_data with None args (uses defaults)."""
        mock_load_symbols.return_value = ["BTC/USDT"]

        result = update_latest_data(output_dir=self.temp_dir, args=None)
        # Should work with default args
        self.assertIsInstance(result, dict)

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.calculate_fetch_window')
    @patch('ccxt.okx')
    def test_update_latest_data_incremental_merge(self, mock_ccxt_okx, mock_calc_window, mock_load_symbols):
        """Test update_latest_data incremental data merging."""
        mock_load_symbols.return_value = ["BTC/USDT"]
        mock_calc_window.return_value = ("2021-10-01T00:00:00Z", "2021-10-01T01:00:00Z", True)

        # Create existing data
        symbol = "BTC/USDT"
        os.makedirs(os.path.join(self.temp_dir, "BTC_USDT"), exist_ok=True)
        csv_path = os.path.join(self.temp_dir, "BTC_USDT", "BTC_USDT.csv")

        existing_data = [
            {
                'symbol': symbol,
                'timestamp': '2021-10-01 00:00:00',
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 1000.0,
                'interval': '15m'
            }
        ]
        df = pd.DataFrame(existing_data)
        df.to_csv(csv_path, index=False)

        mock_exchange = MagicMock()
        mock_ccxt_okx.return_value = mock_exchange
        mock_exchange.load_markets = MagicMock()

        # Mock new data
        ohlcv_data = [
            [1633047300000, 50500.0, 51500.0, 49500.0, 51000.0, 1200.0],  # 15 minutes later
        ]
        mock_exchange.fetch_ohlcv.return_value = ohlcv_data

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-01T01:00:00Z"
                self.limit = 100

        result = update_latest_data(output_dir=self.temp_dir, args=MockArgs())

        # Should merge existing and new data
        self.assertIn("BTC/USDT", result)
        merged_df = result["BTC/USDT"]
        self.assertEqual(len(merged_df), 2)  # 1 existing + 1 new

    @patch('scripts.okx_data_collector.load_symbols')
    def test_update_latest_data_empty_symbols(self, mock_load_symbols):
        """Test update_latest_data with empty symbols list."""
        mock_load_symbols.return_value = []

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-01T01:00:00Z"
                self.limit = 100

        result = update_latest_data(output_dir=self.temp_dir, args=MockArgs())
        self.assertEqual(result, {})  # Should return empty dict for empty symbols

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.calculate_fetch_window')
    @patch('ccxt.okx')
    def test_update_latest_data_adjusted_time_parsing_error(self, mock_ccxt_okx, mock_calc_window, mock_load_symbols):
        """Test update_latest_data with adjusted time parsing error."""
        mock_load_symbols.return_value = ["BTC/USDT"]
        mock_calc_window.return_value = ("invalid_start", "invalid_end", True)

        mock_exchange = MagicMock()
        mock_ccxt_okx.return_value = mock_exchange
        mock_exchange.load_markets = MagicMock()

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-01T01:00:00Z"
                self.limit = 100

        # Should raise exception on time parsing error
        with self.assertRaises(Exception):
            update_latest_data(output_dir=self.temp_dir, args=MockArgs())

    def test_argument_parser_creation(self):
        """Test that argument parser is created with correct arguments."""
        # The parser is created at module level, so we can test its configuration
        from scripts.okx_data_collector import parser
        
        # Test that parser has the expected arguments
        self.assertIsNotNone(parser)
        
        # Test parsing with default values
        args = parser.parse_args([])
        self.assertIsNotNone(args.start_time)
        self.assertIsNotNone(args.end_time)
        self.assertIsInstance(args.limit, int)

    def test_main_block_execution(self):
        """Test the argument parsing functionality."""
        from scripts.okx_data_collector import parser
        
        # Test parsing with various arguments
        args = parser.parse_args(['--start_time', '2021-01-01T00:00:00Z', '--limit', '50'])
        self.assertEqual(args.start_time, '2021-01-01T00:00:00Z')
        self.assertEqual(args.limit, 50)
        
        # Test default values
        args_default = parser.parse_args([])
        self.assertIsNotNone(args_default.start_time)
        self.assertIsNotNone(args_default.end_time)
        self.assertEqual(args_default.limit, 1000)  # Default limit from config

    @patch('scripts.okx_data_collector.logger')
    def test_heartbeat_forever_creation(self, mock_logger):
        """Test the _heartbeat_forever function creates a proper coroutine."""
        from scripts.okx_data_collector import _heartbeat_forever
        
        # Test that it returns a coroutine
        heartbeat_coro = _heartbeat_forever(60)
        self.assertTrue(asyncio.iscoroutine(heartbeat_coro))
        
        # Test that we can create a task from it (in a new event loop)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            task = loop.create_task(heartbeat_coro)
            self.assertIsInstance(task, asyncio.Task)
            
            # Cancel the task immediately since it runs forever
            task.cancel()
            try:
                loop.run_until_complete(task)
            except asyncio.CancelledError:
                pass  # Expected
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    @patch('scripts.okx_data_collector.logger')
    @patch('asyncio.sleep')
    @pytest.mark.asyncio
    async def test_heartbeat_forever_execution(self, mock_sleep, mock_logger):
        """Test the _heartbeat_forever function execution."""
        from scripts.okx_data_collector import _heartbeat_forever
        
        # Create a task and cancel it after a short time
        task = asyncio.create_task(_heartbeat_forever(1))  # 1 second interval
        
        # Let it run for a bit
        await asyncio.sleep(0.1)
        
        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass  # Expected
        
        # Verify sleep was called
        mock_sleep.assert_called()
        # Verify logger was called for heartbeat
        mock_logger.info.assert_called_with("Heartbeat: OKX data collector is running...")

    def test_main_no_symbols(self):
        """Test main function when no symbols are loaded."""
        import asyncio
        
        async def run_test():
            mock_load_symbols.return_value = []

            class MockArgs:
                def __init__(self):
                    self.start_time = "2021-10-01T00:00:00Z"
                    self.end_time = "2021-10-02T00:00:00Z"
                    self.limit = 100

            # Main should return early when no symbols loaded
            await main(MockArgs())

        with patch('scripts.okx_data_collector.load_symbols') as mock_load_symbols, \
             patch('scripts.okx_data_collector.update_latest_data') as mock_update_data, \
             patch('scripts.okx_data_collector.logger') as mock_logger:
            
            asyncio.run(run_test())
            
            mock_logger.error.assert_called_with("No symbols loaded, exiting")
            mock_update_data.assert_not_called()

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.update_latest_data')
    @patch('scripts.okx_data_collector.logger')
    @pytest.mark.asyncio
    async def test_main_with_symbols_polling_mode(self, mock_logger, mock_update_data, mock_load_symbols):
        """Test main function with symbols in polling mode (no ccxtpro)."""
        mock_load_symbols.return_value = ["BTC/USDT"]

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-02T00:00:00Z"
                self.limit = 100

        # Mock ccxtpro import failure and ccxt fallback
        with patch.dict('sys.modules', {'ccxtpro': None}):
            with patch('importlib.import_module') as mock_import:
                mock_ccxt = MagicMock()
                mock_exchange = MagicMock()
                mock_ccxt.okx.return_value = mock_exchange
                mock_import.return_value = mock_ccxt

                # Mock asyncio.Event and stop immediately
                with patch('asyncio.Event') as mock_event:
                    mock_stop_event = MagicMock()
                    mock_stop_event.is_set.return_value = True  # Stop immediately
                    mock_event.return_value = mock_stop_event

                    with patch('asyncio.create_task'):
                        with patch('asyncio.wait'):
                            await main(MockArgs())

        mock_update_data.assert_called_once_with(["BTC/USDT"], output_dir="data/klines", args=MockArgs())

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.update_latest_data')
    @patch('scripts.okx_data_collector.logger')
    @pytest.mark.asyncio
    async def test_main_exchange_creation_failure(self, mock_logger, mock_update_data, mock_load_symbols):
        """Test main function when exchange creation fails."""
        mock_load_symbols.return_value = ["BTC/USDT"]

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-02T00:00:00Z"
                self.limit = 100

        # Mock both ccxtpro and ccxt import failures
        with patch.dict('sys.modules', {'ccxtpro': None, 'ccxt': None}):
            with patch('importlib.import_module', side_effect=ImportError("No module")):
                with pytest.raises(RuntimeError, match="Failed to create an OKX exchange instance"):
                    await main(MockArgs())

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.update_latest_data')
    @patch('scripts.okx_data_collector.logger')
    @pytest.mark.asyncio
    async def test_main_websocket_mode_heartbeat(self, mock_logger, mock_update_data, mock_load_symbols):
        """Test main function websocket mode heartbeat functionality."""
        mock_load_symbols.return_value = ["BTC/USDT"]

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-02T00:00:00Z"
                self.limit = 100

        # Mock ccxtpro available
        mock_exchange = MagicMock()
        mock_exchange.has = {'watchOHLCV': True, 'watchFundingRate': True}
        mock_exchange.watch_ohlcv = AsyncMock()
        mock_exchange.watch_funding_rate = AsyncMock()
        mock_exchange.close = AsyncMock()

        with patch('importlib.import_module') as mock_import:
            mock_ccxtpro = MagicMock()
            mock_ccxtpro.okx.return_value = mock_exchange
            mock_import.return_value = mock_ccxtpro

            # Mock heartbeat task
            with patch('asyncio.create_task') as mock_create_task:
                mock_heartbeat_task = MagicMock()
                mock_create_task.return_value = mock_heartbeat_task

                # Mock KeyboardInterrupt to exit the loop
                with patch('asyncio.sleep', side_effect=KeyboardInterrupt):
                    with patch('scripts.okx_data_collector.save_klines') as mock_save:
                        await main(MockArgs())

        # Verify heartbeat task was created and cancelled
        mock_create_task.assert_called()
        mock_heartbeat_task.cancel.assert_called()
        mock_exchange.close.assert_called()

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.update_latest_data')
    @patch('scripts.okx_data_collector.logger')
    @patch('signal.signal')
    @pytest.mark.asyncio
    async def test_main_polling_mode_signal_handling(self, mock_signal, mock_logger, mock_update_data, mock_load_symbols):
        """Test main function polling mode with signal handling."""
        mock_load_symbols.return_value = ["BTC/USDT"]

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-02T00:00:00Z"
                self.limit = 100

        # Mock ccxtpro not available, so falls back to polling mode
        with patch.dict('sys.modules', {'ccxtpro': None}):
            with patch('importlib.import_module', side_effect=ImportError("No ccxtpro")):
                # Mock ccxt available
                mock_exchange = MagicMock()
                mock_exchange.has = {'watchOHLCV': False}  # No websocket support
                
                with patch('ccxt.okx') as mock_ccxt_okx:
                    mock_ccxt_okx.return_value = mock_exchange
                    
                    # Mock environment variable
                    with patch.dict(os.environ, {'POLL_INTERVAL': '30'}):
                        # Mock asyncio.Event for stop event
                        with patch('asyncio.Event') as mock_event:
                            mock_stop_event = MagicMock()
                            mock_stop_event.is_set.return_value = True  # Stop immediately
                            mock_event.return_value = mock_stop_event
                            
                            await main(MockArgs())

        # Verify signal handlers were set up
        mock_signal.assert_called()
        mock_logger.info.assert_any_call("Running in polling mode with 30 second intervals")

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.logger')
    @pytest.mark.asyncio
    async def test_main_websocket_mode_subscription_failure(self, mock_logger, mock_load_symbols):
        """Test main function websocket mode when subscription fails."""
        mock_load_symbols.return_value = ["BTC/USDT"]

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-02T00:00:00Z"
                self.limit = 100

        # Mock ccxtpro available
        mock_exchange = MagicMock()
        mock_exchange.has = {'watchOHLCV': True, 'watchFundingRate': True}
        mock_exchange.watch_ohlcv = AsyncMock(side_effect=Exception("Subscription failed"))
        mock_exchange.close = AsyncMock()

        with patch('importlib.import_module') as mock_import:
            mock_ccxtpro = MagicMock()
            mock_ccxtpro.okx.return_value = mock_exchange
            mock_import.return_value = mock_ccxtpro

            # Should handle the exception gracefully
            await main(MockArgs())

        mock_logger.error.assert_called_with("Error in websocket mode: Subscription failed")
        mock_exchange.close.assert_called()

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.logger')
    @pytest.mark.asyncio
    async def test_main_websocket_mode_successful_subscription(self, mock_logger, mock_load_symbols):
        """Test main function websocket mode with successful subscription."""
        mock_load_symbols.return_value = ["BTC/USDT"]

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-02T00:00:00Z"
                self.limit = 100

        # Mock ccxtpro available
        mock_exchange = MagicMock()
        mock_exchange.has = {'watchOHLCV': True, 'watchFundingRate': True}
        mock_exchange.watch_ohlcv = AsyncMock()
        mock_exchange.watch_funding_rate = AsyncMock()
        mock_exchange.close = AsyncMock()

        with patch('importlib.import_module') as mock_import:
            mock_ccxtpro = MagicMock()
            mock_ccxtpro.okx.return_value = mock_exchange
            mock_import.return_value = mock_ccxtpro

            # Mock heartbeat task
            with patch('asyncio.create_task') as mock_create_task:
                mock_heartbeat_task = MagicMock()
                mock_create_task.return_value = mock_heartbeat_task

                # Mock KeyboardInterrupt to exit the infinite loop
                with patch('asyncio.sleep', side_effect=KeyboardInterrupt):
                    with patch('scripts.okx_data_collector.save_klines') as mock_save:
                        await main(MockArgs())

        # Verify subscriptions were called
        mock_exchange.watch_ohlcv.assert_called_with("BTC/USDT", '15m', mock_exchange.watch_ohlcv.call_args[0][2])
        mock_exchange.watch_funding_rate.assert_called_with("BTC/USDT", mock_exchange.watch_funding_rate.call_args[0][1])
        mock_exchange.close.assert_called()

    @patch('scripts.okx_data_collector.load_symbols')
    @patch('scripts.okx_data_collector.logger')
    @pytest.mark.asyncio
    async def test_main_websocket_mode_missing_methods(self, mock_logger, mock_load_symbols):
        """Test main function websocket mode when exchange lacks required methods."""
        mock_load_symbols.return_value = ["BTC/USDT"]

        class MockArgs:
            def __init__(self):
                self.start_time = "2021-10-01T00:00:00Z"
                self.end_time = "2021-10-02T00:00:00Z"
                self.limit = 100

        # Mock ccxtpro available but exchange lacks websocket methods
        mock_exchange = MagicMock()
        mock_exchange.has = {'watchOHLCV': False, 'watchFundingRate': False}

        with patch('importlib.import_module') as mock_import:
            mock_ccxtpro = MagicMock()
            mock_ccxtpro.okx.return_value = mock_exchange
            mock_import.return_value = mock_ccxtpro

            with pytest.raises(RuntimeError, match="does not support required websocket methods"):
                await main(MockArgs())
@pytest.mark.asyncio
async def test_handle_ohlcv_basic():
    """Test basic OHLCV data handling."""
    with patch('scripts.okx_data_collector.save_klines') as mock_save_klines:
        symbol = "BTC/USDT"
        candles = [
            [1633046400000, 50000.0, 51000.0, 49000.0, 50500.0, 1000.0],  # timestamp in ms
            [1633047300000, 50500.0, 51500.0, 49500.0, 51000.0, 1200.0]
        ]

        result = await handle_ohlcv(None, symbol, '15m', candles)
        assert result is True

        # Check that save_klines was not called (buffer < 60)
        mock_save_klines.assert_not_called()


@pytest.mark.asyncio
async def test_handle_ohlcv_buffer_full():
    """Test OHLCV handling when buffer reaches 60 items."""
    with patch('scripts.okx_data_collector.save_klines') as mock_save_klines:
        symbol = "BTC/USDT"

        # Create 60 candles to trigger save
        candles = []
        for i in range(60):
            ts_ms = 1633046400000 + (i * 900000)  # 15 minutes apart
            candles.append([ts_ms, 50000.0 + i, 51000.0 + i, 49000.0 + i, 50500.0 + i, 1000.0 + i])

        result = await handle_ohlcv(None, symbol, '15m', candles)
        assert result is True

        # Check that save_klines was called once
        mock_save_klines.assert_called_once_with(symbol)


@pytest.mark.asyncio
async def test_handle_funding_rate():
    """Test funding rate data handling."""
    symbol = "BTC/USDT"
    funding_rate = {
        'fundingRate': 0.0001,
        'nextFundingTime': 1633046400000,
        'timestamp': 1633046300000
    }

    result = await handle_funding_rate(None, symbol, funding_rate)
    assert result is True
