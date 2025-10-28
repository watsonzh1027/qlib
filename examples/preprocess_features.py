#!/usr/bin/env python3
"""
Feature preprocessing and generation for crypto trading
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List
import logging
import argparse
from features.crypto_workflow.model_io import save_model
from qlib.utils.io import write_parquet
from features.crypto_workflow.alpha360 import Alpha360Calculator

# Add qlib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

def compute_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute technical indicators including Alpha360 features."""
    features = {}
    
    # Basic features
    features['returns'] = df['close'].pct_change()
    features['log_returns'] = np.log1p(features['returns'])
    
    # Alpha360 features
    alpha_calculator = Alpha360Calculator()
    alpha_features = alpha_calculator.calculate_features(df)
    for col in alpha_features.columns:
        features[col] = alpha_features[col]
    
    # Traditional technical indicators
    # Moving averages
    for window in [5, 10, 20, 60]:
        features[f'ma_{window}'] = df['close'].rolling(window=window).mean()
        features[f'ma_vol_{window}'] = df['volume'].rolling(window=window).mean()
        
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    features['rsi'] = 100 - (100 / (1 + rs))
    
    # Volatility
    for window in [5, 20]:
        features[f'volatility_{window}'] = features['log_returns'].rolling(window).std()
    
    # OHLCV ratios
    features['hl_ratio'] = df['high'] / df['low']
    features['co_ratio'] = df['close'] / df['open']
    features['vol_ratio'] = df['volume'] / features['ma_vol_20']
    
    return pd.DataFrame(features)

def align_and_fill(df: pd.DataFrame) -> pd.DataFrame:
    """Align index and forward fill/backfill missing values."""
    # Ensure timestamp index
    df.index = pd.to_datetime(df.index)

    # Sort by time
    df = df.sort_index()

    # Forward fill and backfill to handle all missing values
    df = df.fillna(method='ffill')
    df = df.fillna(method='bfill')

    return df

def preprocess_data(input_path: Path, output_path: Path) -> None:
    """Preprocess raw OHLCV data and generate features"""
    pass

def prepare_features(
    ohlcv_path: str,
    symbol: str,
    timeframe: str,
    target_path: str
) -> None:
    """Main feature preparation pipeline."""
    # Load OHLCV data
    df = pd.read_parquet(ohlcv_path)
    
    # Set index to timestamp if not already
    if not isinstance(df.index, pd.DatetimeIndex):
        df.set_index('timestamp', inplace=True)
    
    # Compute features
    features_df = compute_technical_features(df)
    
    # Align and fill missing values
    features_df = align_and_fill(features_df)
    
    # Add metadata columns
    features_df['symbol'] = symbol
    features_df['timeframe'] = timeframe
    
    # Save features
    out_path = Path(target_path) / f"features_{symbol}_{timeframe}.parquet"
    write_parquet(features_df, str(out_path))
    
    # Save feature metadata
    metadata = {
        'symbol': symbol,
        'timeframe': timeframe,
        'feature_columns': list(features_df.columns),
        'row_count': len(features_df),
        'start_time': str(features_df.index.min()),
        'end_time': str(features_df.index.max())
    }
    save_model(metadata, str(out_path.with_suffix('.meta.json')))
    
    logger.info(f"Saved features to {out_path}")
    logger.info(f"Features shape: {features_df.shape}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ohlcv-path', required=True, help='Path to OHLCV parquet file')
    parser.add_argument('--symbol', required=True, help='Trading symbol')
    parser.add_argument('--timeframe', required=True, help='Data timeframe')
    parser.add_argument('--target-path', required=True, help='Output directory for features')
    args = parser.parse_args()
    
    prepare_features(
        args.ohlcv_path,
        args.symbol,
        args.timeframe,
        args.target_path
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
