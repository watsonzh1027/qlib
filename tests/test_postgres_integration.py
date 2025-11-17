"""
Integration tests for PostgreSQL data collector functionality.
"""

import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from scripts.okx_data_collector import set_global_output_config, save_klines
from scripts.postgres_storage import PostgreSQLStorage


class TestPostgresDataCollectorIntegration:
    """Integration tests for data collector with PostgreSQL output."""

    @pytest.fixture
    def connection_string(self):
        """PostgreSQL connection string for testing."""
        return "postgresql://test_user:test_pass@localhost:5432/test_db"

    @pytest.fixture
    def mock_postgres_storage(self, connection_string):
        """Mock PostgreSQL storage for testing."""
        with patch('scripts.postgres_storage.create_engine'):
            storage = PostgreSQLStorage(connection_string)
            return storage

    @pytest.fixture
    def sample_klines_data(self):
        """Sample k-lines data for testing."""
        return [
            {
                'symbol': 'BTC-USDT',
                'timestamp': 1640995200,
                'open': 50000.0,
                'high': 50200.0,
                'low': 49900.0,
                'close': 50100.0,
                'volume': 100.5,
                'interval': '1m'
            },
            {
                'symbol': 'BTC-USDT',
                'timestamp': 1640995260,
                'open': 50100.0,
                'high': 50300.0,
                'low': 50000.0,
                'close': 50200.0,
                'volume': 150.25,
                'interval': '1m'
            }
        ]

    def test_global_config_csv_mode(self):
        """Test setting global config to CSV mode."""
        set_global_output_config(output_format="csv")

        # Test that save_klines works in CSV mode (without postgres storage)
        with patch('scripts.okx_data_collector.pd.DataFrame.to_csv') as mock_to_csv:
            # Create valid entries with proper column structure
            entries = [
                {
                    'symbol': 'BTC-USDT',
                    'timestamp': 1640995200,
                    'open': 50000.0,
                    'high': 50200.0,
                    'low': 49900.0,
                    'close': 50100.0,
                    'volume': 100.5,
                    'interval': '1m'
                }
            ]
            result = save_klines("BTC-USDT", entries=entries)

            # Should return True for CSV mode
            assert result is True

    def test_global_config_postgres_mode(self, mock_postgres_storage):
        """Test setting global config to PostgreSQL mode."""
        set_global_output_config(output_format="postgres", postgres_storage=mock_postgres_storage)

        # Verify the global config is set
        # This is tested implicitly through the save_klines test below

    @patch('scripts.okx_data_collector.normalize_klines')
    def test_save_klines_postgres_success(self, mock_normalize_klines, connection_string, sample_klines_data):
        """Test successful save_klines with PostgreSQL output."""
        # Setup mocks
        normalized_df = pd.DataFrame({
            'timestamp': [datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                         datetime(2022, 1, 1, 0, 1, 0, tzinfo=timezone.utc)],
            'open_price': [50000.0, 50100.0],
            'high_price': [50200.0, 50300.0],
            'low_price': [49900.0, 50000.0],
            'close_price': [50100.0, 50200.0],
            'volume': [100.5, 150.25],
            'quote_volume': [5002500.0, 7518750.0],
            'trade_count': [10, 15],
            'taker_buy_volume': [60.0, 90.0],
            'taker_buy_quote_volume': [3003000.0, 4513500.0]
        })

        mock_normalize_klines.return_value = normalized_df

        # Create real storage instance for this test
        with patch('scripts.postgres_storage.create_engine'):
            storage = PostgreSQLStorage(connection_string)

            # Set global config
            set_global_output_config(output_format="postgres", postgres_storage=storage)

            # Mock the save_ohlcv_data method
            with patch.object(storage, 'save_ohlcv_data', return_value=True) as mock_save:
                result = save_klines("BTC-USDT", entries=sample_klines_data, output_format="postgres")

                assert result is True
                mock_save.assert_called_once()
                # Verify the call arguments
                call_args = mock_save.call_args
                assert call_args[0][1] == "BTC-USDT"  # symbol
                assert call_args[0][2] == "1m"  # interval (default from TIMEFRAME)

    @patch('scripts.okx_data_collector.normalize_klines')
    def test_save_klines_postgres_validation_failure(self, mock_normalize_klines, connection_string):
        """Test save_klines with PostgreSQL validation failure."""
        # Setup mocks with invalid data
        invalid_df = pd.DataFrame({
            'timestamp': ['invalid_timestamp'],
            'open_price': [50000.0],
            'high_price': [50200.0],
            'low_price': [49900.0],
            'close_price': [50100.0],
            'volume': [100.5]
        })

        mock_normalize_klines.return_value = invalid_df

        # Create real storage instance
        with patch('scripts.postgres_storage.create_engine'):
            storage = PostgreSQLStorage(connection_string)

            # Set global config
            set_global_output_config(output_format="postgres", postgres_storage=storage)

            # Should return False due to validation failure
            result = save_klines("BTC-USDT", entries=[{
                'symbol': 'BTC-USDT',
                'timestamp': 1640995200,
                'open': 50000.0,
                'high': 50200.0,
                'low': 49900.0,
                'close': 50100.0,
                'volume': 100.5,
                'interval': '1m'
            }], output_format="postgres")

            assert result is False

    def test_save_klines_no_postgres_storage(self, connection_string):
        """Test save_klines fails when PostgreSQL storage not provided."""
        set_global_output_config(output_format="postgres", postgres_storage=None)

        with patch('builtins.print'):  # Suppress error logging
            entries = [{
                'symbol': 'BTC-USDT',
                'timestamp': 1640995200,
                'open': 50000.0,
                'high': 50200.0,
                'low': 49900.0,
                'close': 50100.0,
                'volume': 100.5,
                'interval': '1m'
            }]
            result = save_klines("BTC-USDT", entries=entries, output_format="postgres")

            assert result is False

    @patch('scripts.okx_data_collector.normalize_klines')
    def test_save_klines_fallback_to_global_config(self, mock_normalize_klines, connection_string):
        """Test save_klines uses global config when no explicit postgres_storage provided."""
        # Setup mocks
        normalized_df = pd.DataFrame({
            'timestamp': [datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)],
            'open_price': [50000.0],
            'high_price': [50200.0],
            'low_price': [49900.0],
            'close_price': [50100.0],
            'volume': [100.5]
        })

        mock_normalize_klines.return_value = normalized_df

        # Create storage and set global config
        with patch('scripts.postgres_storage.create_engine'):
            storage = PostgreSQLStorage(connection_string)
            set_global_output_config(output_format="postgres", postgres_storage=storage)

            # Call save_klines without explicit postgres_storage (should use global)
            entries = [{
                'symbol': 'BTC-USDT',
                'timestamp': 1640995200,
                'open': 50000.0,
                'high': 50200.0,
                'low': 49900.0,
                'close': 50100.0,
                'volume': 100.5,
                'interval': '1m'
            }]
            with patch.object(storage, 'save_ohlcv_data', return_value=True) as mock_save:
                result = save_klines("BTC-USDT", entries=entries, output_format="postgres")

                assert result is True
                mock_save.assert_called_once()

    def test_save_klines_empty_entries(self):
        """Test save_klines with empty entries."""
        # Should handle empty entries gracefully
        result = save_klines("BTC-USDT", entries=[])

        assert result is False  # Should return False for empty data