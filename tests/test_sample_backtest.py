import unittest
import os
from scripts.sample_backtest import run_sample_backtest

class TestSampleBacktest(unittest.TestCase):
    def test_run_sample_backtest(self):
        """
        Test the sample backtest script to ensure it runs without errors.
        """
        data_dir = "test_data/qlib_data"
        os.makedirs(data_dir, exist_ok=True)

        try:
            run_sample_backtest(data_dir=data_dir)
        except Exception as e:
            self.fail(f"Sample backtest failed with error: {e}")
