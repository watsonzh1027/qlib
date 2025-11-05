import unittest
import os
import pandas as pd  # Add this import
from scripts.convert_to_qlib import convert_to_qlib, validate_data_integrity

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
        # Create mock data
        os.makedirs(f"{self.input_dir}/BTC-USDT", exist_ok=True)
        pd.DataFrame({
            "timestamp": [1633046400, 1633047300],
            "open": [50000, 50500],
            "high": [51000, 51500],
            "low": [49000, 49500],
            "close": [50500, 51000],
            "volume": [1000, 1200],
            "symbol": ["BTC-USDT", "BTC-USDT"],
            "interval": ["15min", "15min"]
        }).to_parquet(f"{self.input_dir}/BTC-USDT/BTC-USDT_15min.parquet", index=False)

        # Run conversion
        convert_to_qlib(self.input_dir, self.output_dir)

        # Verify output
        self.assertTrue(os.path.exists(f"{self.output_dir}/BTC-USDT.parquet"))
        self.assertTrue(os.path.exists(f"{self.output_dir}/instruments/all.txt"))
        with open(f"{self.output_dir}/instruments/all.txt", "r") as f:
            instruments = f.read().splitlines()
        self.assertIn("BTC-USDT", instruments)

    def test_validate_data_integrity(self):
        # Valid data
        valid_data = pd.DataFrame({
            "timestamp": [1633046400, 1633047300, 1633048200],  # 15-minute intervals
            "open": [50000, 50500, 51000],
            "high": [51000, 51500, 52000],
            "low": [49000, 49500, 50000],
            "close": [50500, 51000, 51500],
            "volume": [1000, 1200, 1100]
        })
        self.assertTrue(validate_data_integrity(valid_data))

        # Invalid data (missing timestamp)
        invalid_data = pd.DataFrame({
            "timestamp": [1633046400, 1633048200],  # Missing 1633047300
            "open": [50000, 51000],
            "high": [51000, 52000],
            "low": [49000, 50000],
            "close": [50500, 51500],
            "volume": [1000, 1100]
        })
        self.assertFalse(validate_data_integrity(invalid_data))
