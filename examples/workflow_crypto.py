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
from scripts.check_data_quality import check_data_quality
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

def convert_ccxt_to_qlib_freq(freq: str) -> str:
    """Convert CCXT frequency format to QLib frequency format.
    
    Args:
        freq: CCXT frequency string (e.g., '1h', '15m', '1d')
        
    Returns:
        QLib frequency string (e.g., '1hour', '15min', '1day')
    """
    # CCXT to qlib frequency mapping
    freq_mapping = {
        '1m': '1min',
        '3m': '3min', 
        '5m': '5min',
        '15m': '15min',
        '30m': '30min',
        '1h': '60min',
        '2h': '120min',
        '4h': '240min',
        '6h': '360min',
        '8h': '480min',
        '12h': '720min',
        '1d': '1440min',
        '3d': '4320min',
        '1w': '10080min',
        '1M': '43200min'
    }
    
    # If already in pandas format, return as-is
    if freq in freq_mapping.values():
        return freq
        
    # Convert from CCXT format
    if freq in freq_mapping:
        return freq_mapping[freq]
    
    # If not found in mapping, assume it's already in correct format
    logger.warning(f"Unknown frequency format '{freq}', using as-is")
    return freq

def get_ann_scaler(freq: str) -> int:
    """Calculate annualization scaler based on frequency for cryptocurrency markets."""
    
    # First, convert CCXT format to QLib format if needed
    freq = convert_ccxt_to_qlib_freq(freq)
    
    try:
        # Use pandas to parse frequency string and calculate periods in a year
        delta = pd.to_timedelta(freq)
        # Assuming 365 days in a year for crypto (24/7 trading)
        periods_in_year = pd.Timedelta(days=365) / delta
        ann_scaler = int(periods_in_year)
        
        # Validate the calculated ann_scaler
        if ann_scaler <= 0:
            raise ValueError(f"Invalid ann_scaler calculated: {ann_scaler}")
            
        logger.info(f"Calculated ann_scaler={ann_scaler} for frequency='{freq}'")
        return ann_scaler
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse frequency '{freq}': {e}")
        
        # Fallback to predefined mappings for common frequencies
        freq_mapping = {
            '1min': 365 * 24 * 60,      # 1分钟: 365天 × 24小时 × 60分钟
            '5min': 365 * 24 * 12,      # 5分钟: 365天 × 24小时 × 12个5分钟
            '15min': 365 * 24 * 4,       # 15分钟: 365天 × 24小时 × 4个15分钟
            '30min': 365 * 24 * 2,       # 30分钟: 365天 × 24小时 × 2个30分钟
            '1hour': 365 * 24,           # 1小时: 365天 × 24小时
            '4hour': 365 * 6,            # 4小时: 365天 × 6个4小时
            '1day': 365,                 # 1天: 365天
            '1week': 52,                 # 1周: 52周
        }
        
        # Try to find the frequency in the mapping
        for known_freq, scaler in freq_mapping.items():
            if known_freq in freq or freq in known_freq:
                logger.info(f"Using predefined ann_scaler={scaler} for frequency='{freq}'")
                return scaler
        
        # Final fallback for crypto: use daily frequency (365)
        logger.warning(f"Unknown frequency '{freq}', defaulting to crypto daily ann_scaler=365")
        return 365


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

def train_single_crypto_model(config_manager, symbol, qlib):
    """Train a model for a single crypto symbol."""
    logger.info(f"Training model for {symbol}...")
    
    # Set custom instruments to only this symbol
    config_manager.set_custom_instruments([symbol])
    
    # Load dataset for this symbol
    dataset_config = config_manager.get_dataset_config()
    dataset = init_instance_by_config(dataset_config)
    
    # Train model
    model_config_full = config_manager.get_model_config_full()
    model = init_instance_by_config(model_config_full)
    model.fit(dataset)
    
    logger.info(f"Model trained successfully for {symbol}")
    return model, dataset

def generate_signals_for_all_models(models_dict, config_manager, recorder):
    """Generate signals using all trained models."""
    logger.info("Generating signals for all models...")
    
    all_predictions = []
    
    for symbol, (model, dataset) in models_dict.items():
        logger.info(f"Generating signals for {symbol}...")
        
        # Generate prediction for this model
        pred = model.predict(dataset)
        if isinstance(pred, pd.Series):
            pred = pred.to_frame(symbol.replace('/', ''))  # Use qlib format for column name
        
        all_predictions.append(pred)
        logger.info(f"Generated predictions for {symbol} with shape {pred.shape}")
    
    # Combine all predictions
    if all_predictions:
        combined_predictions = pd.concat(all_predictions, axis=1)
        # Save combined predictions
        recorder.save_objects(**{"pred.pkl": combined_predictions})
        logger.info(f"Combined predictions saved with {len(combined_predictions.columns)} symbols: {list(combined_predictions.columns)}")
        
        # Also save labels if available (using first dataset as example)
        first_dataset = next(iter(models_dict.values()))[1]
        if hasattr(first_dataset, 'prepare'):
            try:
                raw_label = SignalRecord.generate_label(first_dataset)
                if raw_label is not None:
                    recorder.save_objects(**{"label.pkl": raw_label})
            except Exception as e:
                logger.warning(f"Could not generate labels: {e}")
    
    return combined_predictions

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
        # Data quality check
        logger.info("Performing data quality checks...")
        if not check_data_quality():
            logger.error("Data quality checks failed. Aborting workflow.")
            sys.exit(1)
        logger.info("Data quality checks passed.")

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

        # Get all symbols for training
        all_symbols = config_manager.get_crypto_symbols()
        logger.info(f"Training models for {len(all_symbols)} crypto symbols: {all_symbols}")
        
        # Train a model for each crypto symbol
        models_dict = {}
        for symbol in all_symbols:
            try:
                model, dataset = train_single_crypto_model(config_manager, symbol, qlib)
                models_dict[symbol] = (model, dataset)
                logger.info(f"Successfully trained model for {symbol}")
            except Exception as e:
                logger.error(f"Failed to train model for {symbol}: {e}")
                continue
        
        if not models_dict:
            raise RuntimeError("No models were successfully trained")
        
        logger.info(f"Successfully trained {len(models_dict)} models")

        # End the MLflow run started by model.fit()
        mlflow.end_run()

        # Generate signals and run backtesting
        logger.info("Generating signals and running backtesting...")

        # Calculate ann_scaler based on workflow frequency
        ann_scaler = get_ann_scaler(config_manager.get_workflow_config()["frequency"])
        logger.info(f"Calculated annualization scaler: {ann_scaler}")
        
        with R.start(experiment_name="crypto_workflow"):
            # Signal generation using all models
            recorder = R.get_recorder()
            combined_predictions = generate_signals_for_all_models(models_dict, config_manager, recorder)
            
            if combined_predictions is None or combined_predictions.empty:
                logger.error("No predictions generated from any model")
                return
            
            logger.info("Signals generated successfully")

            # Signal Analysis
            sar = SigAnaRecord(recorder, ana_long_short=True, ann_scaler=ann_scaler)
            sar.generate()
            logger.info("Signal analysis completed")

            # Data health checks
            perform_data_health_checks(recorder, sar)

            # Portfolio Analysis / Backtesting
            # Use the first model and dataset for port analysis config (qlib requirement)
            first_model, first_dataset = next(iter(models_dict.values()))
            port_analysis_config["strategy"]["kwargs"]["signal"] = (first_model, first_dataset)
            
            par = PortAnaRecord(recorder, port_analysis_config, risk_analysis_freq=config_manager.get_workflow_config()["frequency"])
            par.generate()
            logger.info("Backtesting completed")

        logger.info("Crypto Trading Workflow completed successfully")

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()