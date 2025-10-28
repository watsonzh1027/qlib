import pytest
import pandas as pd
import numpy as np
import time
from features.crypto_workflow.alpha360 import Alpha360Calculator, FeatureGroup, rank, ts_argmax, delta, correlation, ts_rank

@pytest.fixture
def sample_ohlcv():
    """Create sample OHLCV data."""
    dates = pd.date_range('2023-01-01', '2023-01-31', freq='1h')
    df = pd.DataFrame({
        'open': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 101,
        'low': np.random.randn(len(dates)).cumsum() + 99,
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    return df

def test_alpha360_calculator_init():
    """Test Alpha360Calculator initialization."""
    calculator = Alpha360Calculator()
    assert calculator.selected_groups == list(FeatureGroup)
    assert calculator.max_features == 10

    calculator_custom = Alpha360Calculator(selected_groups=[FeatureGroup.PRICE], max_features_per_group=5)
    assert calculator_custom.selected_groups == [FeatureGroup.PRICE]
    assert calculator_custom.max_features == 5

def test_calculate_features_price_group(sample_ohlcv):
    """Test calculate_features for PRICE group."""
    calculator = Alpha360Calculator(selected_groups=[FeatureGroup.PRICE])
    features = calculator.calculate_features(sample_ohlcv)

    expected_columns = ['alpha001', 'alpha002', 'alpha003', 'alpha004', 'alpha005']
    assert list(features.columns) == expected_columns
    for col in features.columns:
        assert isinstance(features[col], pd.Series)
        assert not features[col].isnull().all()
        # Assuming alphas are normalized to [-1, 1] or similar
        assert features[col].min() >= -1
        assert features[col].max() <= 1

def test_calculate_features_volume_group(sample_ohlcv):
    """Test calculate_features for VOLUME group."""
    calculator = Alpha360Calculator(selected_groups=[FeatureGroup.VOLUME])
    features = calculator.calculate_features(sample_ohlcv)

    expected_columns = ['alpha101', 'alpha102', 'alpha103', 'alpha104', 'alpha105']
    assert list(features.columns) == expected_columns
    for col in features.columns:
        assert isinstance(features[col], pd.Series)
        assert not features[col].isnull().all()

def test_calculate_features_momentum_group(sample_ohlcv):
    """Test calculate_features for MOMENTUM group."""
    calculator = Alpha360Calculator(selected_groups=[FeatureGroup.MOMENTUM])
    features = calculator.calculate_features(sample_ohlcv)

    expected_columns = ['alpha201', 'alpha202', 'alpha203', 'alpha204', 'alpha205']
    assert list(features.columns) == expected_columns
    for col in features.columns:
        assert isinstance(features[col], pd.Series)
        assert not features[col].isnull().all()

def test_calculate_features_volatility_group(sample_ohlcv):
    """Test calculate_features for VOLATILITY group."""
    calculator = Alpha360Calculator(selected_groups=[FeatureGroup.VOLATILITY])
    features = calculator.calculate_features(sample_ohlcv)

    expected_columns = ['alpha301', 'alpha302', 'alpha303', 'alpha304', 'alpha305']
    assert list(features.columns) == expected_columns
    for col in features.columns:
        assert isinstance(features[col], pd.Series)
        assert not features[col].isnull().all()

def test_calculate_features_all_groups(sample_ohlcv):
    """Test calculate_features for all groups."""
    calculator = Alpha360Calculator()
    features = calculator.calculate_features(sample_ohlcv)

    # All groups: PRICE (5), VOLUME (5), MOMENTUM (5), VOLATILITY (5) = 20 features
    assert len(features.columns) == 20
    for col in features.columns:
        assert isinstance(features[col], pd.Series)
        assert not features[col].isnull().all()

@pytest.mark.parametrize("group", list(FeatureGroup))
def test_feature_group_properties(sample_ohlcv, group):
    """Test each feature group properties."""
    calculator = Alpha360Calculator(selected_groups=[group])
    features = calculator.calculate_features(sample_ohlcv)

    assert len(features.columns) > 0
    for col in features.columns:
        # Skip initial NaN rows from rolling windows
        clean_series = features[col].iloc[60:]
        assert not clean_series.isnull().any()
        # Allow some flexibility for volatility features that may exceed [-1, 1]
        if group != FeatureGroup.VOLATILITY:
            assert clean_series.min() >= -1
            assert clean_series.max() <= 1

def test_helper_functions():
    """Test helper functions."""
    series = pd.Series([1, 2, 3, 4, 5])

    # Test rank
    ranked = rank(series)
    assert ranked.iloc[0] == 0.2  # pct=True ranks from 0 to 1
    assert ranked.iloc[-1] == 1.0

    # Test delta
    diff = delta(series, 1)
    assert diff.iloc[1] == 1
    assert diff.iloc[0] is pd.NA or np.isnan(diff.iloc[0])

    # Test ts_argmax
    argmax_series = ts_argmax(series, 3)
    assert isinstance(argmax_series, pd.Series)

    # Test correlation
    series2 = pd.Series([5, 4, 3, 2, 1])
    corr = correlation(series, series2, 3)
    assert isinstance(corr, pd.Series)

    # Test ts_rank
    ts_ranked = ts_rank(series, 3)
    assert isinstance(ts_ranked, pd.Series)

def test_feature_correlation(sample_ohlcv):
    """Test feature correlations are not too high."""
    calculator = Alpha360Calculator()
    features = calculator.calculate_features(sample_ohlcv)

    # Remove NaN rows
    features = features.iloc[60:]

    # Calculate correlation matrix
    corr = features.corr()

    # Check no features are too highly correlated (>0.95)
    high_corr = np.where(np.abs(corr) > 0.95)
    high_corr_pairs = list(zip(high_corr[0], high_corr[1]))

    # Exclude self-correlations
    high_corr_pairs = [(features.columns[i], features.columns[j])
                       for i, j in high_corr_pairs
                       if i < j]

    assert len(high_corr_pairs) == 0, f"Found highly correlated features: {high_corr_pairs}"

def test_feature_importance(sample_ohlcv):
    """Test feature importance ranking."""
    calculator = Alpha360Calculator()
    features = calculator.calculate_features(sample_ohlcv)

    # Create synthetic target (next period returns)
    target = sample_ohlcv['close'].pct_change().shift(-1)

    # Remove NaN rows
    features = features.iloc[60:-1]
    target = target.iloc[60:-1]

    # Calculate IC (Information Coefficient)
    ic = pd.DataFrame({col: features[col].corr(target) for col in features.columns}, index=['IC'])

    # Verify some features have meaningful IC (relaxed threshold for synthetic data)
    assert (abs(ic) > 0.05).any().any(), "No features show meaningful predictive power"

def test_all_alpha_functions_existence():
    """Test all alpha functions are implemented and accessible."""
    calculator = Alpha360Calculator()
    for group in FeatureGroup:
        group_funcs = calculator._feature_functions[group]
        assert len(group_funcs) > 0, f"No functions implemented for {group.value}"
        
        # Test each function can be called
        for name, func in group_funcs.items():
            assert callable(func), f"Function {name} in {group.value} is not callable"

def test_error_handling_invalid_data(sample_ohlcv):
    """Test error handling with invalid input data."""
    calculator = Alpha360Calculator()

    # Test with missing columns - should raise KeyError when accessing missing column
    bad_df = sample_ohlcv.drop('volume', axis=1)
    with pytest.raises(KeyError, match="'volume'"):
        calculator.calculate_features(bad_df)

    # Test with NaN values
    bad_df = sample_ohlcv.copy()
    bad_df.loc[bad_df.index[0:10], 'close'] = np.nan
    features = calculator.calculate_features(bad_df)
    assert not features.isnull().all().all(), "All features should not be NaN"

def test_feature_computation_speed():
    """Test feature computation performance."""
    # Create larger dataset
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='1h')
    df = pd.DataFrame({
        'open': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 101,
        'low': np.random.randn(len(dates)).cumsum() + 99,
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    
    calculator = Alpha360Calculator()
    
    # Measure computation time
    start_time = time.time()
    features = calculator.calculate_features(df)
    end_time = time.time()
    
    computation_time = end_time - start_time
    rows_per_second = len(df) / computation_time
    
    # Performance assertions
    assert computation_time < 60, f"Feature computation took too long: {computation_time:.2f}s"
    assert rows_per_second > 1000, f"Processing speed too slow: {rows_per_second:.0f} rows/s"

def test_memory_usage():
    """Test memory usage during feature computation."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Create medium-sized dataset
    dates = pd.date_range('2022-01-01', '2023-12-31', freq='1h')
    df = pd.DataFrame({
        'open': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 101,
        'low': np.random.randn(len(dates)).cumsum() + 99,
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    
    calculator = Alpha360Calculator()
    features = calculator.calculate_features(df)
    
    peak_memory = process.memory_info().rss
    memory_increase = (peak_memory - initial_memory) / (1024 * 1024)  # MB
    
    # Memory usage assertions
    assert memory_increase < 1000, f"Memory usage too high: {memory_increase:.1f}MB"

def test_numerical_stability():
    """Test numerical stability with extreme values."""
    dates = pd.date_range('2023-01-01', '2023-01-31', freq='1h')
    n = len(dates)
    df = pd.DataFrame({
        'open': [1e9, 1e-9] * (n // 2) + [1e9] if n % 2 else [],
        'high': [1e9, 1e-9] * (n // 2) + [1e9] if n % 2 else [],
        'low': [1e9, 1e-9] * (n // 2) + [1e9] if n % 2 else [],
        'close': [1e9, 1e-9] * (n // 2) + [1e9] if n % 2 else [],
        'volume': [1e9, 1e-9] * (n // 2) + [1e9] if n % 2 else []
    }, index=dates)

    calculator = Alpha360Calculator()
    features = calculator.calculate_features(df)

    # Check for infinities
    assert not np.isinf(features.values).any(), "Infinite values found"

    # Check that not all columns are completely NaN (some features may have NaNs due to extreme values)
    nan_columns = np.isnan(features.values).all(axis=0)
    assert not nan_columns.all(), f"All columns are NaN: {features.columns[nan_columns].tolist()}"

    # Check that at least some features have valid values
    valid_features = ~nan_columns
    assert valid_features.any(), "No features have any valid values"

def test_feature_consistency():
    """Test feature consistency with different data sizes."""
    calculator = Alpha360Calculator()

    # Calculate features for different data sizes
    sizes = [200, 400, 800]  # Start with larger sizes to avoid NaN issues
    results = []

    for size in sizes:
        dates = pd.date_range('2023-01-01', periods=size, freq='1h')
        df = pd.DataFrame({
            'open': np.random.randn(size).cumsum() + 100,
            'high': np.random.randn(size).cumsum() + 101,
            'low': np.random.randn(size).cumsum() + 99,
            'close': np.random.randn(size).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, size)
        }, index=dates)

        features = calculator.calculate_features(df)
        results.append(features.iloc[-100:])  # Compare last 100 rows

    # Check feature consistency (relaxed threshold for synthetic data)
    for i in range(len(results)-1):
        for col in results[i].columns:
            correlation = results[i][col].corr(results[i+1][col])
            # Skip if correlation is NaN (due to constant values)
            if not np.isnan(correlation):
                assert correlation > 0.95, f"Feature {col} not consistent across different data sizes: {correlation:.3f}"
