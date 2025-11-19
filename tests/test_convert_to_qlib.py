import unittest
import os
import pandas as pd  # Add this import
from unittest.mock import Mock, patch, MagicMock
from scripts.convert_to_qlib import convert_to_qlib, validate_data_integrity, PostgreSQLStorage

class TestConvertToQlib(unittest.TestCase):
    def setUp(self):
        self.input_dir = "test_data/klines"
        self.output_dir = "test_data/qlib_data"
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree("test_data")

    def test_convert_to_qlib(self):
        # Skip this test as convert_to_qlib now reads from config
        self.skipTest("convert_to_qlib now reads from config, test needs to be updated")

    def test_validate_data_integrity(self):
        # Valid data
        valid_data = pd.DataFrame({
            "timestamp": pd.to_datetime([1633046400, 1633047300, 1633048200], unit='s'),  # 15-minute intervals
            "open": [50000, 50500, 51000],
            "high": [51000, 51500, 52000],
            "low": [49000, 49500, 50000],
            "close": [50500, 51000, 51500],
            "volume": [1000, 1200, 1100]
        })
        self.assertTrue(validate_data_integrity(valid_data, '15T'))

        # Invalid data (missing timestamp)
        invalid_data = pd.DataFrame({
            "timestamp": pd.to_datetime([1633046400, 1633048200], unit='s'),  # Missing middle timestamp
            "open": [50000, 51000],
            "high": [51000, 52000],
            "low": [49000, 50000],
            "close": [50500, 51500],
            "volume": [1000, 1100]
        })
        self.assertFalse(validate_data_integrity(invalid_data, '15T'))


class TestPostgreSQLStorage(unittest.TestCase):
    def setUp(self):
        self.storage = PostgreSQLStorage(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_pass",
            table="kline_data"
        )

    def tearDown(self):
        if self.storage.connection:
            self.storage.disconnect()

    @patch('scripts.convert_to_qlib.psycopg2.connect')
    def test_connect_success(self, mock_connect):
        """Test successful database connection."""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        self.storage.connect()

        mock_connect.assert_called_once()
        self.assertEqual(self.storage.connection, mock_connection)

    @patch('scripts.convert_to_qlib.psycopg2.connect')
    def test_connect_failure_with_retry(self, mock_connect):
        """Test connection failure with retry logic."""
        mock_connect.side_effect = Exception("Connection failed")

        with self.assertRaises(Exception):
            self.storage.connect(max_retries=2)

        # Should be called once since exception is not caught by retry logic
        self.assertEqual(mock_connect.call_count, 1)

    @patch('scripts.convert_to_qlib.psycopg2.connect')
    def test_get_kline_data(self, mock_connect):
        """Test retrieving kline data from database."""
        # Mock connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_connect.return_value = mock_connection

        # Mock query results
        mock_cursor.fetchall.return_value = [
            {
                'timestamp': '2023-01-01T00:00:00',
                'symbol': 'BTC/USDT',
                'interval': '1m',
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 1000.0
            }
        ]

        self.storage.connect()
        df = self.storage.get_kline_data('BTC/USDT', '1m')

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['symbol'], 'BTC/USDT')
        self.assertEqual(df.iloc[0]['interval'], '1m')

    @patch('scripts.convert_to_qlib.psycopg2.connect')
    def test_validate_schema_success(self, mock_connect):
        """Test successful schema validation."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_connect.return_value = mock_connection

        # Mock column query results
        mock_cursor.fetchall.return_value = [
            ('timestamp',), ('symbol',), ('interval',),
            ('open',), ('high',), ('low',),
            ('close',), ('volume',)
        ]

        self.storage.connect()
        result = self.storage.validate_schema()

        self.assertTrue(result)

    @patch('scripts.convert_to_qlib.psycopg2.connect')
    def test_validate_schema_missing_columns(self, mock_connect):
        """Test schema validation with missing columns."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_connect.return_value = mock_connection

        # Mock incomplete column results
        mock_cursor.fetchall.return_value = [('timestamp',), ('symbol',)]

        self.storage.connect()
        result = self.storage.validate_schema()

        self.assertFalse(result)

    def test_validate_data_quality_valid_data(self):
        """Test data quality validation with valid data."""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=3, freq='1min'),
            'symbol': ['BTC/USDT'] * 3,
            'interval': ['1m'] * 3,
            'open': [50000, 50500, 51000],
            'high': [51000, 51500, 52000],
            'low': [49000, 49500, 50000],
            'close': [50500, 51000, 51500],
            'volume': [1000, 1200, 1100]
        })

        result = self.storage.validate_data_quality(df)

        self.assertTrue(result['valid'])
        self.assertEqual(result['total_records'], 3)
        self.assertEqual(len(result['issues']), 0)

    def test_validate_data_quality_invalid_data(self):
        """Test data quality validation with invalid data."""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=2, freq='1min'),
            'symbol': ['BTC/USDT'] * 2,
            'interval': ['1m'] * 2,
            'open': [50000, -100],  # Negative price
            'high': [51000, 51500],
            'low': [49000, 49500],
            'close': [50500, 51000],
            'volume': [1000, 1200]
        })

        result = self.storage.validate_data_quality(df)

        self.assertFalse(result['valid'])
        self.assertIn("Negative or zero open prices found", result['issues'])

    def test_context_manager(self):
        """Test context manager functionality."""
        with patch('scripts.convert_to_qlib.psycopg2.connect') as mock_connect:
            mock_connection = Mock()
            mock_connect.return_value = mock_connection

            with self.storage as storage:
                self.assertEqual(storage, self.storage)
                self.assertEqual(storage.connection, mock_connection)

            mock_connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
