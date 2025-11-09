#!/usr/bin/env python3
"""
Crypto Trading Workflow

This script implements a complete quantitative trading workflow for cryptocurrency data using qlib framework.
Based on workflow_by_code.py but adapted for crypto markets with 15-minute data and OKX exchange.

Features:
- Load crypto OHLCV data from qlib data provider
- Train machine learning models (GBDT) on crypto data
- Generate trading signals
- Perform backtesting with crypto-specific parameters
- Generate analysis reports

Usage:
    python examples/workflow_crypto.py
"""

import sys
import os
import logging
from pathlib import Path

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.config_manager import ConfigManager
from qlib.utils import init_instance_by_config
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, PortAnaRecord, SigAnaRecord
import mlflow

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_data_availability():
    """Verify that crypto data is available and accessible."""
    config_manager = ConfigManager()
    data_config = config_manager.config.get('data', {})

    bin_data_dir = data_config.get('bin_data_dir', 'data/qlib_data')
    data_path = project_root / bin_data_dir

    if not data_path.exists():
        raise FileNotFoundError(f"Crypto data directory not found: {data_path}")

    logger.info(f"Crypto data directory verified: {data_path}")
    return str(data_path)

def initialize_qlib_crypto(data_path):
    """Initialize qlib with crypto data provider."""
    import qlib
    from qlib.constant import REG_CN  # Using CN region for now, may need crypto-specific

    logger.info(f"Initializing qlib with data path: {data_path}")
    qlib.init(provider_uri=data_path, region=REG_CN)
    logger.info("Qlib initialized successfully for crypto data")

    return qlib

def load_crypto_dataset(qlib, config_manager):
    """Load and prepare crypto dataset for training."""
    from qlib.data.dataset import DatasetH

    logger.info("Loading crypto dataset...")

    # Get dataset configuration from config manager
    dataset_config = config_manager.get_dataset_config()

    dataset = init_instance_by_config(dataset_config)
    logger.info("Crypto dataset loaded successfully")

    return dataset

def train_crypto_model(dataset, model_config_full):
    """Train machine learning model on crypto dataset."""
    logger.info("Training crypto model...")

    model = init_instance_by_config(model_config_full)
    model.fit(dataset)
    logger.info("Crypto model trained successfully")

    return model

def main():
    """Main workflow execution function."""
    logger.info("Starting Crypto Trading Workflow")

    try:
        # Load configuration
        config_manager = ConfigManager()
        workflow_config = config_manager.get_workflow_config()
        model_config = config_manager.get_model_config()
        model_config_full = config_manager.get_model_config_full()
        data_handler_config = config_manager.get_data_handler_config()
        trading_config = config_manager.get_trading_config()
        backtest_config = config_manager.get_backtest_config()
        port_analysis_config = config_manager.get_port_analysis_config()

        logger.info(f"Workflow config: {workflow_config}")
        logger.info(f"Model config: {model_config}")
        logger.info(f"Model config full: {model_config_full}")
        logger.info(f"Data handler config: {data_handler_config}")
        logger.info(f"Trading config: {trading_config}")
        logger.info(f"Backtest config: {backtest_config}")
        logger.info(f"Port analysis config: {port_analysis_config}")

        # Verify data availability
        data_path = verify_data_availability()

        # Initialize qlib
        qlib = initialize_qlib_crypto(data_path)

        # Load and prepare dataset
        dataset = load_crypto_dataset(qlib, config_manager)

        # Train model
        model = train_crypto_model(dataset, model_config_full)

        # End the MLflow run started by model.fit()
        mlflow.end_run()

        # Generate signals and run backtesting
        logger.info("Generating signals and running backtesting...")

        # Add signal to strategy kwargs
        port_analysis_config["strategy"]["kwargs"]["signal"] = (model, dataset)

        with R.start(experiment_name="crypto_workflow"):
            # Signal generation
            recorder = R.get_recorder()
            sr = SignalRecord(model, dataset, recorder)
            sr.generate()
            logger.info("Signals generated successfully")

            # Signal Analysis
            sar = SigAnaRecord(recorder)
            sar.generate()
            logger.info("Signal analysis completed")

            # Portfolio Analysis / Backtesting
            par = PortAnaRecord(recorder, port_analysis_config, "15min")
            par.generate()
            logger.info("Backtesting completed")

        logger.info("Crypto Trading Workflow completed successfully")

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()