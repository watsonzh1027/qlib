import unittest
import os
import shutil
from scripts.sample_backtest import run_sample_backtest

class TestSampleBacktest(unittest.TestCase):
    def test_run_sample_backtest(self):
        """
        Test the sample backtest script to ensure it runs without errors.
        """
        # Remove the `data_dir` argument and ensure the directory exists
        os.makedirs("test_data/qlib_data", exist_ok=True)
        # Ensure the qlib_data directory is populated with required data for testing
        source_data_dir = "data/qlib_data"
        test_data_dir = "test_data/qlib_data"
        if not os.path.exists(test_data_dir):
            if os.path.exists(source_data_dir):
                shutil.copytree(source_data_dir, test_data_dir)
            else:
                raise FileNotFoundError(f"Source data directory '{source_data_dir}' does not exist.")
        try:
            run_sample_backtest()
        except Exception as e:
            self.fail(f"Sample backtest failed with error: {e}")
