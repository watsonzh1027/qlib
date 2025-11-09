import unittest
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from okx_data_collector import normalize_klines


class TestNormalizeKlines(unittest.TestCase):

    def test_normalize_empty_dataframe(self):
        """Test that empty DataFrame is returned unchanged."""
        df = pd.DataFrame()
        result = normalize_klines(df)
        self.assertTrue(result.empty)

    def test_normalize_single_record(self):
        """Test normalization with a single record."""
        data = [{
            'symbol': 'BTC/USDT',
            'timestamp': pd.Timestamp('2023-01-01 10:00:00'),
            'open': 50000.0,
            'high': 51000.0,
            'low': 49000.0,
            'close': 50500.0,
            'volume': 100.0,
            'interval': '15m'
        }]
        df = pd.DataFrame(data)
        result = normalize_klines(df)

        # Check that all columns are preserved
        expected_columns = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'interval']
        self.assertEqual(set(result.columns), set(expected_columns))

        # Check that timestamp is datetime
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result.iloc[0]['timestamp'], pd.Timestamp)

    def test_normalize_removes_duplicates(self):
        """Test that duplicate timestamps are removed, keeping first."""
        data = [
            {
                'symbol': 'BTC/USDT',
                'timestamp': pd.Timestamp('2023-01-01 10:00:00'),
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 100.0,
                'interval': '15m'
            },
            {
                'symbol': 'BTC/USDT',
                'timestamp': pd.Timestamp('2023-01-01 10:00:00'),  # duplicate
                'open': 50500.0,
                'high': 51500.0,
                'low': 49500.0,
                'close': 51000.0,
                'volume': 110.0,
                'interval': '15m'
            }
        ]
        df = pd.DataFrame(data)
        result = normalize_klines(df)

        # Should have only one record (first duplicate removed)
        self.assertEqual(len(result), 1)
        # Should keep the first occurrence
        self.assertEqual(result.iloc[0]['close'], 50500.0)

    def test_normalize_sorts_by_timestamp(self):
        """Test that records are sorted by timestamp."""
        data = [
            {
                'symbol': 'BTC/USDT',
                'timestamp': pd.Timestamp('2023-01-01 10:15:00'),
                'open': 50500.0,
                'high': 51500.0,
                'low': 49500.0,
                'close': 51000.0,
                'volume': 110.0,
                'interval': '15m'
            },
            {
                'symbol': 'BTC/USDT',
                'timestamp': pd.Timestamp('2023-01-01 10:00:00'),
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 100.0,
                'interval': '15m'
            }
        ]
        df = pd.DataFrame(data)
        result = normalize_klines(df)

        # Should be sorted by timestamp
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]['timestamp'], pd.Timestamp('2023-01-01 10:00:00'))
        self.assertEqual(result.iloc[1]['timestamp'], pd.Timestamp('2023-01-01 10:15:00'))

    def test_normalize_preserves_all_columns(self):
        """Test that all required columns are preserved."""
        data = [{
            'symbol': 'BTC/USDT',
            'timestamp': pd.Timestamp('2023-01-01 10:00:00'),
            'open': 50000.0,
            'high': 51000.0,
            'low': 49000.0,
            'close': 50500.0,
            'volume': 100.0,
            'interval': '15m'
        }]
        df = pd.DataFrame(data)
        result = normalize_klines(df)

        # Check all columns exist
        required_columns = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'interval']
        for col in required_columns:
            self.assertIn(col, result.columns)

        # Check data integrity
        self.assertEqual(result.iloc[0]['symbol'], 'BTC/USDT')
        self.assertEqual(result.iloc[0]['open'], 50000.0)
        self.assertEqual(result.iloc[0]['interval'], '15m')


if __name__ == '__main__':
    unittest.main()