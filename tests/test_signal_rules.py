import pandas as pd
import pytest
import sys
from pathlib import Path
import features

# Add project root to path
root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from features.crypto_workflow.signal_rules import score_to_signal

def test_score_to_signal_basic():
    # Test data
    print("Importing signal_rules module...")
    print(f"Module path: {features.crypto_workflow.signal_rules.__file__}")
    print(f"Current sys.path: {sys.path}")
    scores_df = pd.DataFrame({
        'ts': pd.date_range('2023-01-01', periods=5),
        'symbol': ['BTC-USDT'] * 5,
        'score': [0.8, 0.6, 0.2, 0.4, 0.9]
    })
    
    # Default thresholds test
    signals_df = score_to_signal(scores_df)
    
    # Verify signal mapping
    expected_signals = ['BUY', 'HOLD', 'SELL', 'HOLD', 'BUY']
    assert list(signals_df['signal']) == expected_signals
    
    # Verify position sizes are between 0 and 1
    assert all((0 <= x <= 1) for x in signals_df['position_size'])

def test_score_to_signal_custom_thresholds():
    scores_df = pd.DataFrame({
        'ts': pd.date_range('2023-01-01', periods=3),
        'symbol': ['ETH-USDT'] * 3,
        'score': [0.9, 0.5, 0.1]
    })
    
    custom_config = {
        'buy': 0.8,
        'sell': 0.2,
        'max_position': 0.5
    }
    
    signals_df = score_to_signal(scores_df, custom_config)
    
    # Verify signals with custom thresholds
    expected_signals = ['BUY', 'HOLD', 'SELL']
    assert list(signals_df['signal']) == expected_signals
    
    # Verify max position size respected
    assert all(x <= 0.5 for x in signals_df['position_size'])
