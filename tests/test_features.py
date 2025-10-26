import pytest
import pandas as pd
import numpy as np
from qlib.features.crypto import generate_features, calc_technical_features

def test_feature_generation():
    """Test basic feature generation pipeline"""
    # Create sample OHLCV data
    dates = pd.date_range("2024-01-01", "2024-01-10", freq="15min", tz="UTC")
    ohlcv = pd.DataFrame({
        "open": np.random.random(len(dates)) * 100 + 40000,
        "high": np.random.random(len(dates)) * 100 + 40100,
        "low": np.random.random(len(dates)) * 100 + 39900,
        "close": np.random.random(len(dates)) * 100 + 40000,
        "volume": np.random.random(len(dates)) * 1000
    }, index=dates)

    features = generate_features(ohlcv)
    
    # Verify feature properties
    assert isinstance(features, pd.DataFrame)
    assert len(features) == len(ohlcv)
    assert "target" in features.columns
    assert not features.isnull().any().any()

def test_technical_features():
    """Test technical indicator generation"""
    # Create trending price series
    dates = pd.date_range("2024-01-01", "2024-01-10", freq="15min", tz="UTC")
    close = pd.Series(np.linspace(40000, 41000, len(dates)), index=dates)
    
    features = calc_technical_features(close)
    
    # Verify technical indicators
    assert "rsi" in features.columns
    assert "macd" in features.columns
    assert "bb_upper" in features.columns
