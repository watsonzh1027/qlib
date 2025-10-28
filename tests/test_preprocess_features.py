import pytest
import pandas as pd
import numpy as np
from examples.preprocess_features import compute_technical_features, align_and_fill, prepare_features
from features.crypto_workflow.alpha360 import Alpha360Calculator
from pathlib import Path

@pytest.fixture
def sample_ohlcv():
    """Create realistic OHLCV data with gaps and outliers."""
    dates = pd.date_range('2023-01-01', '2023-01-31', freq='1h')
    np.random.seed(42)
    
    df = pd.DataFrame({
        'open': 100 + np.random.randn(len(dates)).cumsum(),
        'high': 101 + np.random.randn(len(dates)).cumsum(),
        'low': 99 + np.random.randn(len(dates)).cumsum(),
        'close': 100 + np.random.randn(len(dates)).cumsum(),
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    
    # Add some gaps (NaN values)
    df.iloc[10:15] = np.nan
    df.iloc[100:102] = np.nan
    
    # Add some outliers
    df.iloc[50, df.columns.get_loc('volume')] *= 10
    df.iloc[150, df.columns.get_loc('close')] *= 1.5
    
    return df

def test_align_and_fill(sample_ohlcv):
    """Test timestamp alignment and NaN filling."""
    filled_df = align_and_fill(sample_ohlcv)
    
    # Check no NaNs remain
    assert not filled_df.isnull().any().any()
    
    # Check index is datetime and sorted
    assert isinstance(filled_df.index, pd.DatetimeIndex)
    assert filled_df.index.is_monotonic_increasing
    
    # Check forward fill worked correctly
    gap_start = sample_ohlcv.index[10]
    assert filled_df.loc[gap_start]['close'] == sample_ohlcv.iloc[9]['close']

def test_compute_technical_features(sample_ohlcv):
    """Test technical indicator computation."""
    features = compute_technical_features(sample_ohlcv)
    
    # Check required features exist
    required_features = [
        'returns', 'log_returns', 'ma_5', 'ma_20',
        'rsi', 'volatility_5', 'hl_ratio'
    ]
    assert all(f in features.columns for f in required_features)
    
    # Verify feature properties
    assert features['returns'].mean() != 0  # Should have non-zero mean returns
    assert (features['ma_5'] > 0).all()  # Moving averages should be positive
    assert (features['rsi'] >= 0).all() and (features['rsi'] <= 100).all()  # RSI bounds

def test_alpha360_integration(sample_ohlcv):
    """Test Alpha360 features integration with preprocessing."""
    calculator = Alpha360Calculator()
    alpha_features = calculator.calculate_features(sample_ohlcv)
    
    # Check each feature group has values
    for group in calculator.selected_groups:
        group_features = [col for col in alpha_features.columns 
                         if col.startswith(group.value)]
        assert len(group_features) > 0
        
        # Check feature properties
        for feature in group_features:
            series = alpha_features[feature].dropna()
            assert len(series) > 0
            # Most alpha features should be normalized
            assert -2 <= series.min() <= series.max() <= 2

def test_prepare_features_end_to_end(tmp_path, sample_ohlcv):
    """Test complete feature preparation pipeline."""
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
    
    # Check basic properties
    assert not features.isnull().any().any()
    assert 'symbol' in features.columns
    assert 'timeframe' in features.columns
    
    # Check all feature groups present
    tech_features = ['returns', 'ma_5', 'rsi']
    alpha_features = ['alpha001', 'alpha101', 'alpha201', 'alpha301']
    
    assert all(f in features.columns for f in tech_features)
    assert all(f in features.columns for f in alpha_features)
    
    # Verify feature correlations are reasonable
    corr = features.select_dtypes(include=[np.number]).corr()
    # No perfect correlations (except self-correlations)
    assert (abs(corr.values[~np.eye(corr.shape[0], dtype=bool)]) < 0.999).all()

def test_preprocessing_performance(sample_ohlcv):
    """Test preprocessing performance and memory usage."""
    import time
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    start_mem = process.memory_info().rss
    start_time = time.time()
    
    # Run feature computation
    features = compute_technical_features(sample_ohlcv)
    calculator = Alpha360Calculator()
    alpha_features = calculator.calculate_features(sample_ohlcv)
    
    end_time = time.time()
    end_mem = process.memory_info().rss
    
    # Performance assertions
    assert end_time - start_time < 5.0  # Should complete within 5 seconds
    memory_increase_mb = (end_mem - start_mem) / (1024 * 1024)
    assert memory_increase_mb < 100  # Memory increase should be reasonable

def test_error_handling_invalid_input(tmp_path):
    """Test preprocessing error handling."""
    # Invalid data types
    with pytest.raises(TypeError):
        prepare_features(123, "BTC-USDT", "1h", str(tmp_path))
    
    # Missing columns
    bad_df = pd.DataFrame({'close': [1,2,3]})
    bad_path = tmp_path / "bad.parquet"
    bad_df.to_parquet(str(bad_path))
    
    with pytest.raises(ValueError):
        prepare_features(str(bad_path), "BTC-USDT", "1h", str(tmp_path))

def test_preprocessing_large_dataset(tmp_path):
    """Test preprocessing performance with large dataset."""
    # Create large dataset
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='5min')
    df = pd.DataFrame({
        'open': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 101,
        'low': np.random.randn(len(dates)).cumsum() + 99,
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    
    input_path = tmp_path / "large_ohlcv.parquet"
    df.to_parquet(str(input_path))
    
    start_time = time.time()
    prepare_features(str(input_path), "BTC-USDT", "5min", str(tmp_path))
    processing_time = time.time() - start_time
    
    assert processing_time < 120, f"Processing took too long: {processing_time:.1f}s"

def test_memory_usage_preprocessing(tmp_path, sample_ohlcv):
    """Test memory efficiency of preprocessing."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    input_path = tmp_path / "test_ohlcv.parquet"
    sample_ohlcv.to_parquet(str(input_path))
    
    prepare_features(str(input_path), "BTC-USDT", "1h", str(tmp_path))
    
    peak_memory = process.memory_info().rss
    memory_increase = (peak_memory - initial_memory) / (1024 * 1024)  # MB
    
    assert memory_increase < 500, f"Memory usage too high: {memory_increase:.1f}MB"
