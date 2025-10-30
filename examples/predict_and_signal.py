#!/usr/bin/env python3
"""
Model prediction and signal generation script
"""
import sys
from pathlib import Path
import logging
import argparse
import pandas as pd
import numpy as np
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from features.crypto_workflow.model_io import load_model
from features.crypto_workflow.signal_rules import score_to_signal
from qlib.utils.io import write_parquet

logger = logging.getLogger(__name__)

def generate_signals(model_path: Path, data_path: Path, output_path: Path) -> None:
    """Generate trading signals using trained model"""
    pass

def predict_signals(
    model_path: str,
    features_path: str,
    output_path: str,
    threshold_config: dict = None
) -> pd.DataFrame:
    """Load model, make predictions and generate signals."""
    logger.info(f"Loading model from {model_path}")
    # Load model
    model, _ = load_model(model_path)
    logger.info("Model loaded successfully")

    logger.info(f"Loading features from {features_path}")
    # Load features
    features_df = pd.read_parquet(features_path)
    logger.info(f"Features loaded: {features_df.shape[0]} rows, {features_df.shape[1]} columns")

    # Select only numeric columns for prediction (LightGBM requirement)
    numeric_features = features_df.select_dtypes(include=[np.number])
    logger.info(f"Selected {numeric_features.shape[1]} numeric feature columns for prediction")

    # Generate predictions
    logger.info("Generating predictions...")
    scores = model.predict(numeric_features)
    logger.info(f"Predictions generated: {len(scores)} scores")

    # Create signals DataFrame
    signals_df = pd.DataFrame({
        'ts': features_df.index,
        'symbol': features_df['symbol'] if 'symbol' in features_df else None,
        'score': scores
    })
    logger.info(f"Signals DataFrame created with {len(signals_df)} rows")

    # Convert scores to signals using signal rules
    logger.info("Converting scores to trading signals...")
    signals_with_pos = score_to_signal(signals_df, threshold_config)
    logger.info(f"Signals generated: {len(signals_with_pos)} total signals")

    # Save signals
    logger.info(f"Saving signals to {output_path}")
    write_parquet(signals_with_pos, output_path)
    logger.info("Signals saved successfully")

    # Print summary
    signal_counts = signals_with_pos['signal'].value_counts() if 'signal' in signals_with_pos.columns else {}
    logger.info(f"Signal summary: {dict(signal_counts)}")

    return signals_with_pos

def main():
    """Main entry point for prediction and signal generation."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser()
    parser.add_argument('--model-path', required=True, help='Path to saved model')
    parser.add_argument('--features-path', required=True, help='Path to features parquet')
    parser.add_argument('--output-path', required=True, help='Path to save signals')
    parser.add_argument('--config', help='Path to threshold config YAML')

    args = parser.parse_args()

    logger.info("Starting prediction and signal generation")
    logger.info(f"Model path: {args.model_path}")
    logger.info(f"Features path: {args.features_path}")
    logger.info(f"Output path: {args.output_path}")
    if args.config:
        logger.info(f"Config path: {args.config}")

    threshold_config = None
    if args.config:
        with open(args.config) as f:
            threshold_config = yaml.safe_load(f)
        logger.info("Threshold config loaded")

    result = predict_signals(args.model_path, args.features_path, args.output_path, threshold_config)
    logger.info("Prediction and signal generation completed successfully")

    return result

if __name__ == "__main__":
    main()
