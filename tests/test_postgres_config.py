"""
Unit tests for PostgreSQL configuration management.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from scripts.postgres_config import PostgresConfig


class TestPostgresConfig:
    """Test cases for PostgresConfig class."""

    def test_default_initialization(self):
        """Test config initialization with default values."""
        config = PostgresConfig(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass"
        )

        assert config.host == "localhost"
        assert config.database == "test_db"
        assert config.user == "test_user"
        assert config.password == "test_pass"
        assert config.port == 5432  # default
        assert config.pool_size == 10  # default
        assert config.max_overflow == 20  # default
        assert config.pool_timeout == 30  # default

    def test_from_env_complete(self):
        """Test loading complete config from environment variables."""
        env_vars = {
            "POSTGRES_HOST": "prod-db.example.com",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "prod_crypto",
            "POSTGRES_USER": "crypto_user",
            "POSTGRES_PASSWORD": "secure_password",
            "POSTGRES_POOL_SIZE": "20",
            "POSTGRES_MAX_OVERFLOW": "40",
            "POSTGRES_POOL_TIMEOUT": "60"
        }

        with patch.dict(os.environ, env_vars):
            config = PostgresConfig.from_env()

            assert config.host == "prod-db.example.com"
            assert config.port == 5433
            assert config.database == "prod_crypto"
            assert config.user == "crypto_user"
            assert config.password == "secure_password"
            assert config.pool_size == 20
            assert config.max_overflow == 40
            assert config.pool_timeout == 60

    def test_from_env_missing_required(self):
        """Test error when required environment variables are missing."""
        minimal_env = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user"
            # Missing POSTGRES_PASSWORD
        }

        with patch.dict(os.environ, minimal_env):
            with pytest.raises(ValueError, match="Missing required environment variable"):
                PostgresConfig.from_env()

    def test_from_env_with_defaults(self):
        """Test loading config with some defaults."""
        env_vars = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test_db",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_pass"
            # No port specified, should use default
        }

        with patch.dict(os.environ, env_vars):
            config = PostgresConfig.from_env()

            assert config.port == 5432  # default
            assert config.pool_size == 10  # default

    def test_from_file_json(self, tmp_path):
        """Test loading config from JSON file."""
        config_data = {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "user": "test_user",
            "password": "test_pass",
            "pool_size": 15
        }

        config_file = tmp_path / "config.json"
        import json
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        config = PostgresConfig.from_file(str(config_file))

        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "test_db"
        assert config.user == "test_user"
        assert config.password == "test_pass"
        assert config.pool_size == 15

    def test_from_file_yaml(self, tmp_path):
        """Test that YAML files are not supported (only JSON)."""
        config_yaml = """
host: localhost
port: 5432
database: test_db
user: test_user
password: test_pass
pool_size: 15
"""

        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            f.write(config_yaml)

        # Should fail because it's not JSON
        with pytest.raises(Exception):  # JSONDecodeError
            PostgresConfig.from_file(str(config_file))

    def test_from_file_invalid_format(self, tmp_path):
        """Test error with invalid file format."""
        config_file = tmp_path / "config.txt"
        with open(config_file, 'w') as f:
            f.write("invalid format")

        with pytest.raises(Exception):  # JSONDecodeError for invalid JSON
            PostgresConfig.from_file(str(config_file))

    def test_from_file_not_found(self):
        """Test error when config file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            PostgresConfig.from_file("/nonexistent/file.json")

    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = PostgresConfig(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass",
            pool_size=5,
            max_overflow=10
        )

        # Should not raise any exception
        config.validate()

    def test_validate_invalid_pool_size(self):
        """Test validation error for invalid pool_size."""
        config = PostgresConfig(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass",
            pool_size=0  # Invalid: must be >= 1
        )

        with pytest.raises(ValueError, match="pool_size must be >= 1"):
            config.validate()

    def test_validate_invalid_max_overflow(self):
        """Test validation error for invalid max_overflow."""
        config = PostgresConfig(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass",
            max_overflow=-1  # Invalid: must be >= 0
        )

        with pytest.raises(ValueError, match="max_overflow must be >= 0"):
            config.validate()

    def test_connection_string_generation(self):
        """Test PostgreSQL connection string generation."""
        config = PostgresConfig(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_pass"
        )

        expected = "postgresql://test_user:test_pass@localhost:5432/test_db"
        assert config.get_connection_string() == expected

    def test_supported_intervals(self):
        """Test that supported intervals are properly configured."""
        config = PostgresConfig(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass"
        )

        expected_intervals = [
            '1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'
        ]
        assert config.supported_intervals == expected_intervals

    def test_retention_days(self):
        """Test that retention days are properly configured."""
        config = PostgresConfig(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass"
        )

        expected_retention = {
            '1m': 365,    # 1 year
            '5m': 365,    # 1 year
            '15m': 730,   # 2 years
            '1h': 730,    # 2 years
            '4h': 1095,   # 3 years
            '1d': -1      # indefinite
        }
        assert config.retention_days == expected_retention