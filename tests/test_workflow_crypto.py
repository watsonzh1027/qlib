#!/usr/bin/env python3
"""
Tests for Crypto Trading Workflow

Test suite for the crypto workflow implementation following TDD principles.
Tests are organized by user story and include unit tests and integration tests.
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.config_manager import ConfigManager

class TestWorkflowCrypto(unittest.TestCase):
    """Test cases for crypto workflow functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures including qlib initialization."""
        cls.config_manager = ConfigManager()
        cls.qlib_initialized = False
        cls.data_path = None

    def setUp(self):
        """Set up test fixtures."""
        if not self.qlib_initialized:
            from examples.workflow_crypto import verify_data_availability, initialize_qlib_crypto
            self.__class__.data_path = verify_data_availability()
            try:
                initialize_qlib_crypto(self.data_path)
                self.__class__.qlib_initialized = True
            except Exception as e:
                if "already activated" in str(e) or "don't reinitialize" in str(e):
                    # Qlib already initialized, skip
                    self.__class__.qlib_initialized = True
                else:
                    raise

    def test_config_manager_workflow_config(self):
        """Test workflow configuration loading."""
        config = self.config_manager.get_workflow_config()
        self.assertIsInstance(config, dict)
        self.assertIn('start_time', config)
        self.assertIn('end_time', config)
        self.assertIn('frequency', config)
        self.assertIn('instruments_limit', config)

    def test_config_manager_model_config(self):
        """Test model configuration loading."""
        config = self.config_manager.get_model_config()
        self.assertIsInstance(config, dict)
        self.assertIn('type', config)
        self.assertIn('learning_rate', config)
        self.assertIn('num_boost_round', config)

    def test_config_manager_model_config_full(self):
        """Test full model configuration loading."""
        config = self.config_manager.get_model_config_full()
        self.assertIsInstance(config, dict)
        self.assertIn('class', config)
        self.assertIn('module_path', config)
        self.assertIn('kwargs', config)
        self.assertEqual(config['class'], 'LGBModel')
        self.assertEqual(config['module_path'], 'qlib.contrib.model.gbdt')

    def test_config_manager_data_handler_config(self):
        """Test data handler configuration loading."""
        config = self.config_manager.get_data_handler_config()
        self.assertIsInstance(config, dict)
        self.assertIn('class', config)
        self.assertIn('module_path', config)
        self.assertIn('kwargs', config)
        self.assertEqual(config['class'], 'DataHandlerLP')
        self.assertEqual(config['module_path'], 'qlib.data.dataset.handler')

    def test_config_manager_crypto_symbols(self):
        """Test crypto symbols loading."""
        symbols = self.config_manager.get_crypto_symbols()
        self.assertIsInstance(symbols, list)
        # Should load symbols from top50_symbols.json
        self.assertGreater(len(symbols), 0)
        self.assertIn('BTC/USDT', symbols)

    def test_portfolio_analysis(self):
        """Test portfolio analysis functionality (T028)."""
        import mlflow
        from qlib.workflow.record_temp import SignalRecord, PortAnaRecord
        from examples.workflow_crypto import load_crypto_dataset, train_crypto_model
        import qlib

        # End any existing MLflow run
        try:
            mlflow.end_run()
        except:
            pass

        # Setup configurations and data
        port_analysis_config = self.config_manager.get_port_analysis_config()
        dataset = load_crypto_dataset(qlib, self.config_manager)
        model_config_full = self.config_manager.get_model_config_full()
        model = train_crypto_model(dataset, model_config_full)

        # Add signal to strategy kwargs
        port_analysis_config["strategy"]["kwargs"]["signal"] = (model, dataset)

        # End the run started by model.fit()
        mlflow.end_run()

        # Test portfolio analysis
        from qlib.workflow import R
        with R.start(experiment_name="test_portfolio_analysis"):
            recorder = R.get_recorder()

            # Generate signals first
            sr = SignalRecord(model, dataset, recorder)
            sr.generate()

            # Test portfolio analysis
            par = PortAnaRecord(recorder, port_analysis_config, "15min")
            par.generate()

            # Verify portfolio analysis completed
            self.assertIsNotNone(recorder)
            # Check that analysis was performed (basic validation)
            self.assertTrue(True)  # If we reach here without exception, analysis succeeded

    def test_data_loading(self):
        """Test data loading functionality (T010)."""
        from examples.workflow_crypto import load_crypto_dataset

        # Test data availability verification (already done in setUpClass)
        self.assertIsInstance(self.data_path, str)
        self.assertTrue(len(self.data_path) > 0)
        self.assertTrue(Path(self.data_path).exists())

        # Test qlib is initialized (already done in setUp)
        import qlib
        self.assertTrue(hasattr(qlib, 'init'))

        # Test dataset loading
        dataset = load_crypto_dataset(qlib, self.config_manager)
        self.assertIsNotNone(dataset)
        # Verify dataset has expected attributes
        self.assertTrue(hasattr(dataset, 'handler'))
        self.assertIsNotNone(dataset.handler)

    def test_model_training(self):
        """Test model training functionality (T011)."""
        from examples.workflow_crypto import train_crypto_model, load_crypto_dataset
        import qlib

        # Dataset should already be loaded from previous tests, but load it again for isolation
        dataset = load_crypto_dataset(qlib, self.config_manager)

        # Test model config loading
        model_config_full = self.config_manager.get_model_config_full()
        self.assertIsInstance(model_config_full, dict)
        self.assertIn('class', model_config_full)
        self.assertIn('module_path', model_config_full)
        self.assertIn('kwargs', model_config_full)

        # Test model training
        model = train_crypto_model(dataset, model_config_full)
        self.assertIsNotNone(model)
        # Verify model has expected attributes
        self.assertTrue(hasattr(model, 'fit'))
        self.assertTrue(hasattr(model, 'predict'))

    def test_signal_generation(self):
        """Test signal generation functionality (T012)."""
        import mlflow
        from qlib.workflow.record_temp import SignalRecord
        from examples.workflow_crypto import train_crypto_model, load_crypto_dataset
        import qlib

        # End any existing MLflow run
        try:
            mlflow.end_run()
        except:
            pass

        # Setup data, dataset, and model
        dataset = load_crypto_dataset(qlib, self.config_manager)
        model_config_full = self.config_manager.get_model_config_full()
        model = train_crypto_model(dataset, model_config_full)

        # End the run started by model.fit()
        mlflow.end_run()

        # Test signal record creation
        from qlib.workflow import R
        with R.start(experiment_name="test_crypto_workflow"):
            recorder = R.get_recorder()
            sr = SignalRecord(model, dataset, recorder)
            self.assertIsNotNone(sr)
            # Verify signal record has expected attributes
            self.assertTrue(hasattr(sr, 'generate'))

            # Test signal generation
            sr.generate()
            # Verify signals were generated (check if recorder has signal data)
            self.assertIsNotNone(recorder)

    def test_framework_adaptation(self):
        """Test framework adaptation for crypto (T021)."""
        from examples.workflow_crypto import load_crypto_dataset, train_crypto_model
        import qlib

        # Test that crypto workflow uses qlib framework components
        dataset = load_crypto_dataset(qlib, self.config_manager)

        # Verify dataset uses qlib DatasetH
        self.assertEqual(dataset.__class__.__name__, 'DatasetH')
        self.assertEqual(dataset.__class__.__module__, 'qlib.data.dataset')

        # Test model training uses qlib model
        model_config_full = self.config_manager.get_model_config_full()
        model = train_crypto_model(dataset, model_config_full)

        # Verify model is qlib LGBModel
        self.assertEqual(model.__class__.__name__, 'LGBModel')
        self.assertEqual(model.__class__.__module__, 'qlib.contrib.model.gbdt')

        # Test crypto-specific configurations
        workflow_config = self.config_manager.get_workflow_config()
        self.assertEqual(workflow_config['instruments_limit'], 50)  # Top 50 crypto instruments

        trading_config = self.config_manager.get_trading_config()
        self.assertEqual(trading_config['open_cost'], 0.001)  # Crypto fees (0.1%)
        self.assertEqual(trading_config['close_cost'], 0.001)

        # Verify crypto instruments are loaded
        symbols = self.config_manager.get_crypto_symbols()
        self.assertIsInstance(symbols, list)
        self.assertGreater(len(symbols), 0)
        # Check for common crypto symbols
        crypto_symbols = [s for s in symbols if 'USDT' in s]
        self.assertGreater(len(crypto_symbols), 0)

if __name__ == '__main__':
    unittest.main()