"""
Unit tests for PostgreSQL storage functionality.
"""

import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call
from scripts.postgres_storage import PostgreSQLStorage, DataValidationError, DatabaseError, DuplicateDataError


class TestPostgreSQLStorage:
    """Test cases for PostgreSQLStorage class."""

    @pytest.fixture
    def connection_string(self):
        """PostgreSQL connection string for testing."""
        return "postgresql://test_user:test_pass@localhost:5432/test_db"

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Sample OHLCV DataFrame for testing."""
        data = {
            'timestamp': [
                datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 1, 1, 12, 1, 0, tzinfo=timezone.utc)
            ],
            'open_price': [50000.0, 50100.0],
            'high_price': [50200.0, 50300.0],
            'low_price': [49900.0, 50000.0],
            'close_price': [50100.0, 50200.0],
            'volume': [100.5, 150.25],
            'quote_volume': [5002500.0, 7518750.0],
            'trade_count': [10, 15],
            'taker_buy_volume': [60.0, 90.0],
            'taker_buy_quote_volume': [3003000.0, 4513500.0]
        }
        return pd.DataFrame(data)

    def test_initialization_success(self, connection_string):
        """Test successful initialization."""
        with patch('scripts.postgres_storage.create_engine') as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            # Mock connection test
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn

            storage = PostgreSQLStorage(connection_string)

            assert storage.engine == mock_engine
            mock_create_engine.assert_called_once()
            mock_conn.execute.assert_called_once()

    def test_data_validation_valid_data(self, connection_string, sample_ohlcv_data):
        """Test data validation with valid OHLCV data."""
        with patch('scripts.postgres_storage.create_engine'):
            storage = PostgreSQLStorage(connection_string)

            # Should not raise any exception
            storage._validate_ohlcv_data(sample_ohlcv_data)

    def test_data_validation_missing_required_columns(self, connection_string):
        """Test data validation with missing required columns."""
        with patch('scripts.postgres_storage.create_engine'):
            storage = PostgreSQLStorage(connection_string)

            invalid_data = pd.DataFrame({
                'timestamp': [datetime.now(timezone.utc)],
                'open_price': [50000.0]
                # Missing high_price, low_price, close_price, volume
            })

            with pytest.raises(DataValidationError, match="Missing required columns"):
                storage._validate_ohlcv_data(invalid_data)

    def test_data_validation_invalid_timestamp_type(self, connection_string):
        """Test data validation with invalid timestamp type."""
        with patch('scripts.postgres_storage.create_engine'):
            storage = PostgreSQLStorage(connection_string)

            invalid_data = pd.DataFrame({
                'timestamp': ['2024-01-01 12:00:00'],  # String instead of datetime
                'open_price': [50000.0],
                'high_price': [50200.0],
                'low_price': [49900.0],
                'close_price': [50100.0],
                'volume': [100.5]
            })

            with pytest.raises(DataValidationError, match="timestamp column must be timezone-aware datetime"):
                storage._validate_ohlcv_data(invalid_data)

    def test_data_validation_negative_prices(self, connection_string):
        """Test data validation with negative prices."""
        with patch('scripts.postgres_storage.create_engine'):
            storage = PostgreSQLStorage(connection_string)

            invalid_data = pd.DataFrame({
                'timestamp': [datetime.now(timezone.utc)],
                'open_price': [-50000.0],  # Negative price
                'high_price': [50200.0],
                'low_price': [49900.0],
                'close_price': [50100.0],
                'volume': [100.5]
            })

            with pytest.raises(DataValidationError, match="Prices must be positive"):
                storage._validate_ohlcv_data(invalid_data)

    @patch('scripts.postgres_storage.sessionmaker')
    def test_save_ohlcv_data_success(self, mock_sessionmaker, connection_string, sample_ohlcv_data):
        """Test successful OHLCV data saving."""
        with patch('scripts.postgres_storage.create_engine'):
            storage = PostgreSQLStorage(connection_string)

            # Mock session
            mock_session = MagicMock()
            mock_sessionmaker.return_value.return_value.__enter__.return_value = mock_session

            result = storage.save_ohlcv_data(sample_ohlcv_data, "BTC-USDT", "1m")

            assert result is True
            # Verify session.execute was called
            assert mock_session.execute.called
            mock_session.commit.assert_called_once()

    def test_save_ohlcv_data_empty_dataframe(self, connection_string):
        """Test save_ohlcv_data with empty DataFrame."""
        with patch('scripts.postgres_storage.create_engine'):
            storage = PostgreSQLStorage(connection_string)

            empty_df = pd.DataFrame()
            result = storage.save_ohlcv_data(empty_df, "BTC-USDT", "1m")

            assert result is True  # Should handle empty data gracefully

    def test_bulk_insert_success(self, connection_string, sample_ohlcv_data):
        """Test successful bulk insert."""
        with patch('scripts.postgres_storage.create_engine'):
            storage = PostgreSQLStorage(connection_string)

            # Convert DataFrame to list of dicts
            data_list = sample_ohlcv_data.to_dict('records')
            for record in data_list:
                record.update({'symbol': 'BTC-USDT', 'interval': '1m'})

            with patch.object(storage, 'save_ohlcv_data') as mock_save:
                mock_save.return_value = True

                result = storage.bulk_insert(data_list)

                assert result == len(data_list)
                mock_save.assert_called_once()

    def test_bulk_insert_inconsistent_symbols(self, connection_string):
        """Test bulk insert with inconsistent symbols."""
        with patch('scripts.postgres_storage.create_engine'):
            storage = PostgreSQLStorage(connection_string)

            data_list = [
                {'symbol': 'BTC-USDT', 'interval': '1m', 'timestamp': datetime.now(timezone.utc),
                 'open_price': 50000.0, 'high_price': 50200.0, 'low_price': 49900.0,
                 'close_price': 50100.0, 'volume': 100.5},
                {'symbol': 'ETH-USDT', 'interval': '1m', 'timestamp': datetime.now(timezone.utc),
                 'open_price': 3000.0, 'high_price': 3100.0, 'low_price': 2950.0,
                 'close_price': 3050.0, 'volume': 200.0}
            ]

            with pytest.raises(DataValidationError, match="All records must have same symbol and interval"):
                storage.bulk_insert(data_list)