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
import pandas as pd

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

def get_ann_scaler(freq: str) -> int:
    """Calculate annualization scaler based on frequency."""
    try:
        # Use pandas to parse frequency string and calculate periods in a year
        delta = pd.to_timedelta(freq)
        # Assuming 365 days in a year for crypto
        periods_in_year = pd.Timedelta(days=365) / delta
        return int(periods_in_year)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse frequency '{freq}'. Defaulting ann_scaler to 252.")
        # Fallback for common qlib daily frequency
        if freq.lower() == 'day':
            return 365
        return 252 # Default for traditional markets


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
    # Use sequential backend and single kernel to avoid parallel processing issues in tests
    qlib.init(provider_uri=data_path, region=REG_CN, joblib_backend="sequential", kernels=1)
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

def perform_data_health_checks(recorder, sig_ana_record):
    """Perform health checks on signal analysis results to detect issues early."""
    logger.info("Performing data health checks...")

    try:
        # Check signal record for NaN values and basic statistics
        signal_df = recorder.load_object("pred.pkl")
        if signal_df is not None:
            nan_count = signal_df.isna().sum().sum()
            if nan_count > 0:
                logger.warning(f"Signal predictions contain {nan_count} NaN values")
            else:
                logger.info("Signal predictions are clean (no NaN values)")

            # Check signal statistics
            signal_mean = signal_df.mean().mean()
            signal_std = signal_df.std().mean()
            logger.info(f"Signal statistics - Mean: {signal_mean:.4f}, Std: {signal_std:.4f}")

            # Check for unrealistic signal values
            if signal_std < 1e-6:
                logger.warning("Signal standard deviation is very low, model may not be learning")
        else:
            logger.warning("Could not load signal predictions from recorder")

        # Try to get any saved analysis results
        try:
            # List all available artifacts
            artifacts = recorder.list_artifacts()
            logger.info(f"Available artifacts: {artifacts}")

            # Look for analysis artifacts
            for artifact in artifacts:
                if 'analysis' in artifact.lower() or 'ic' in artifact.lower():
                    logger.info(f"Found analysis artifact: {artifact}")
                    try:
                        analysis_data = recorder.load_object(artifact)
                        logger.info(f"Analysis data type: {type(analysis_data)}")
                        if isinstance(analysis_data, dict):
                            logger.info(f"Analysis data keys: {list(analysis_data.keys())}")
                            # Try to extract IC values from dict
                            ic_val = analysis_data.get('IC')
                            if ic_val is not None:
                                logger.info(f"IC value from {artifact}: {ic_val}")
                                if abs(ic_val) > 0.95:
                                    logger.warning(f"IC ({ic_val}) is unrealistically high, possible data leakage")
                                elif abs(ic_val) < 0.01:
                                    logger.warning(f"IC ({ic_val}) is very low, model may have no predictive power")
                        elif hasattr(analysis_data, '__dict__'):
                            logger.info(f"Analysis data attributes: {[attr for attr in dir(analysis_data) if not attr.startswith('_')]}")
                    except Exception as e:
                        logger.info(f"Could not extract IC from {artifact}: {e}")
        except:
            pass

        logger.info("Data health checks completed")

    except Exception as e:
        logger.error(f"Error during data health checks: {e}")
        # Don't fail the workflow for health check errors


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

        # Calculate ann_scaler based on workflow frequency
        ann_scaler = get_ann_scaler(config_manager.get_workflow_config()["frequency"])
        logger.info(f"Calculated annualization scaler: {ann_scaler}")
        with R.start(experiment_name="crypto_workflow"):
            # Signal generation
            recorder = R.get_recorder()
            sr = SignalRecord(model, dataset, recorder)
            sr.generate()
            logger.info("Signals generated successfully")

            # Signal Analysis
            sar = SigAnaRecord(recorder, ana_long_short=True, ann_scaler=ann_scaler)
            sar.generate()
            logger.info("Signal analysis completed")

            # Data health checks
            perform_data_health_checks(recorder, sar)

            # Portfolio Analysis / Backtesting
            par = PortAnaRecord(recorder, port_analysis_config, risk_analysis_freq=config_manager.get_workflow_config()["frequency"])
            par.generate()
            logger.info("Backtesting completed")

        logger.info("Crypto Trading Workflow completed successfully")

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()