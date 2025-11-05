import unittest
import os
from unittest.mock import patch
from scripts.okx_data_collector import save_ohlcv_to_parquet, save_funding_rate_to_parquet
from datetime import datetime

class TestOKXDataCollector(unittest.TestCase):
    def test_save_ohlcv_to_parquet(self):
        symbol = "BTC-USDT"
        ohlcv_data = [[1633046400, 50000, 51000, 49000, 50500, 1000]]
        save_ohlcv_to_parquet(symbol, ohlcv_data, "15min", output_dir="test_data/klines")
        self.assertTrue(os.path.exists("test_data/klines/BTC-USDT/BTC-USDT_15min.parquet"))

    @patch("scripts.okx_data_collector.datetime")
    def test_save_funding_rate_to_parquet(self, mock_datetime):
        mock_datetime.utcnow.return_value = datetime(2025, 1, 5)
        mock_datetime.strftime = datetime.strftime

        funding_data = [{"symbol": "BTC-USDT", "timestamp": 1633046400, "funding_rate": 0.0001}]
        save_funding_rate_to_parquet(funding_data, output_dir="test_data/funding")
        self.assertTrue(os.path.exists("test_data/funding/funding_rates_20250105.parquet"))
