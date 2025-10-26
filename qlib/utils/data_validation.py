import pandas as pd
import numpy as np
from pathlib import Path
import json

def validate_ohlcv(df: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, dict]:
    """Validate OHLCV data quality and return validation report"""
    report = {
        "total_rows": len(df),
        "missing_rows": df.isnull().sum().to_dict(),
        "gaps_detected": 0,
        "outliers_detected": 0,
        "valid_rows": 0
    }
    
    # Check price validity
    invalid_prices = (df[['open', 'high', 'low', 'close']] <= 0).any(axis=1)
    df['valid_prices'] = ~invalid_prices
    
    # Check high/low consistency
    df['valid_hl'] = (df['high'] >= df['low']) & (df['high'] >= df['open']) & (df['high'] >= df['close'])
    
    # Detect gaps
    expected_index = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq=df.index.freq
    )
    missing_times = expected_index.difference(df.index)
    report["gaps_detected"] = len(missing_times)
    
    # Flag outliers
    price_jumps = df['close'].pct_change().abs() > config['data_validation']['outliers']['price_jump']
    volume_spikes = df['volume'] > df['volume'].rolling(96).mean() * config['data_validation']['outliers']['volume_spike']
    df['is_outlier'] = price_jumps | volume_spikes
    report["outliers_detected"] = df['is_outlier'].sum()
    
    # Summarize valid data
    df['is_valid'] = (
        df['valid_prices'] &
        df['valid_hl'] &
        ~df['is_outlier']
    )
    report["valid_rows"] = df['is_valid'].sum()
    
    return df, report
