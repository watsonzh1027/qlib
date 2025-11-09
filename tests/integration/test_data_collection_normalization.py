import unittest
import os
import tempfile
import pandas as pd
import sys
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from okx_data_collector import update_latest_data, save_klines


class TestDataCollectionNormalization(unittest.TestCase):

    def setUp(self):
        # Create temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('okx_data_collector.load_symbols')
    def test_data_collection_with_normalization(self, mock_load_symbols):
        """Test that data collection produces normalized CSV files."""
        # Mock symbols
        mock_load_symbols.return_value = ['BTC/USDT']

        # Mock the args object
        class MockArgs:
            def __init__(self):
                self.start_time = '2023-01-01T00:00:00Z'
                self.end_time = '2023-01-01T01:00:00Z'
                self.limit = 10

        args = MockArgs()

        # Mock the REST API call to return sample data
        sample_data = [
            {
                'symbol': 'BTC/USDT',
                'timestamp': pd.Timestamp('2023-01-01 00:45:00'),  # Later timestamp first
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 100.0,
                'interval': '15m'
            },
            {
                'symbol': 'BTC/USDT',
                'timestamp': pd.Timestamp('2023-01-01 00:30:00'),
                'open': 49500.0,
                'high': 50500.0,
                'low': 48500.0,
                'close': 50000.0,
                'volume': 90.0,
                'interval': '15m'
            },
            {
                'symbol': 'BTC/USDT',
                'timestamp': pd.Timestamp('2023-01-01 00:30:00'),  # Duplicate
                'open': 49500.0,
                'high': 50500.0,
                'low': 48500.0,
                'close': 49900.0,  # Different close
                'volume': 95.0,
                'interval': '15m'
            }
        ]

        # Test save_klines with normalization
        result = save_klines('BTC/USDT', base_dir=self.temp_dir, entries=sample_data)
        self.assertTrue(result)

        # Check if file was created
        expected_file = os.path.join(self.temp_dir, "BTC_USDT", "BTC_USDT.csv")
        self.assertTrue(os.path.exists(expected_file))

        # Load and verify the saved data
        df = pd.read_csv(expected_file)

        # Should have 2 records (duplicate removed)
        self.assertEqual(len(df), 2)

        # Should be sorted by timestamp
        timestamps = pd.to_datetime(df['timestamp'])
        self.assertTrue(timestamps.is_monotonic_increasing)

        # First record should be the earlier timestamp
        self.assertEqual(df.iloc[0]['close'], 50000.0)  # First occurrence of duplicate
        self.assertEqual(df.iloc[1]['close'], 50500.0)

        # All required columns should be present
        required_columns = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'interval']
        for col in required_columns:
            self.assertIn(col, df.columns)

    def test_empty_data_handling(self):
        """Test that empty data is handled gracefully."""
        # Test with empty entries
        result = save_klines('BTC/USDT', base_dir=self.temp_dir, entries=[])
        self.assertFalse(result)  # Should return False for empty data

        # No file should be created
        expected_file = os.path.join(self.temp_dir, "BTC_USDT", "BTC_USDT.csv")
        self.assertFalse(os.path.exists(expected_file))


if __name__ == '__main__':
    unittest.main()