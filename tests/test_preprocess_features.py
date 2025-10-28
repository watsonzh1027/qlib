import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from examples.preprocess_features import compute_technical_features, align_and_fill, prepare_features

@pytest.fixture
def sample_ohlcv():
    """Create sample OHLCV data."""
    dates = pd.date_range('2023-01-01', '2023-01-10', freq='1h')
    df = pd.DataFrame({
        'open': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 101,
        'low': np.random.randn(len(dates)).cumsum() + 99,
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    return df

def test_compute_technical_features(sample_ohlcv):
    """Test feature computation produces expected columns without NaNs."""
    features = compute_technical_features(sample_ohlcv)
    
    # Check required features exist
    required_features = [
        'returns', 'log_returns', 'ma_5', 'ma_20',
        'rsi', 'volatility_5', 'hl_ratio'
    ]
    assert all(f in features.columns for f in required_features)
    
    # Initial rows will have NaNs due to rolling windows
    features = features.iloc[60:]  # Skip initial window period
    assert not features.isnull().any().any()

def test_align_and_fill():
    """Test timestamp alignment and filling."""
    dates = pd.date_range('2023-01-01', '2023-01-05', freq='1h')
    df = pd.DataFrame({
        'a': np.random.randn(len(dates)),
        'b': np.random.randn(len(dates))
    }, index=dates)
    
    # Insert some NaN values
    df.iloc[2:4, 0] = np.nan
    
    filled_df = align_and_fill(df)
    assert not filled_df.isnull().any().any()
    assert filled_df.index.equals(dates)

def test_prepare_features(tmp_path, sample_ohlcv):
    """Test end-to-end feature preparation."""
    # Save sample OHLCV
    ohlcv_path = tmp_path / "ohlcv.parquet"
    sample_ohlcv.to_parquet(str(ohlcv_path))
    
    # Run feature preparation
    target_path = tmp_path / "features"
    target_path.mkdir()
    
    prepare_features(
        str(ohlcv_path),
        "BTC-USDT",
        "1h",
        str(target_path)
    )
    
    # Verify outputs
    feature_file = target_path / "features_BTC-USDT_1h.parquet"
    meta_file = feature_file.with_suffix('.meta.json')
    
    assert feature_file.exists()
    assert meta_file.exists()
    
    # Load and verify features
    features = pd.read_parquet(str(feature_file))
    assert not features.isnull().any().any()
    assert 'symbol' in features.columns
    assert 'timeframe' in features.columns
