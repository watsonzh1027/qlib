import pytest
import pandas as pd
import numpy as np
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

    # Verify some features have meaningful IC
    assert (abs(ic) > 0.1).any().any(), "No features show meaningful predictive power"
