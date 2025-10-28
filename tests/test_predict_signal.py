import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import sys
import yaml

# Add project root to path
root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from qlib.examples.predict_and_signal import predict_signals, main
from features.crypto_workflow.model_io import save_model

class MockModel:
    def predict(self, features):
        # Generate synthetic predictions between 0 and 1
        # Return predictions matching the number of input rows
        n_rows = len(features)
        return np.array([0.2, 0.8, 0.5, 0.3, 0.9][:n_rows])

def test_predict_signal_flow():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create paths
        model_path = Path(tmpdir) / "test_model.pkl"
        features_path = Path(tmpdir) / "test_features.parquet"
        signals_path = Path(tmpdir) / "test_signals.parquet"
        
        # Save mock model
        model = MockModel()
        save_model(model, str(model_path))
        
        # Create synthetic features
        features_df = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [0.1, 0.2, 0.3, 0.4, 0.5],
            'symbol': ['BTC-USDT'] * 5
        }, index=pd.date_range('2024-01-01', periods=5, freq='1D'))
        features_df.to_parquet(str(features_path))
        
        # Run predict and signal generation
        signals_df = predict_signals(
            model_path=str(model_path),
            features_path=str(features_path),
            output_path=str(signals_path)
        )
        
        # Validate outputs
        assert isinstance(signals_df, pd.DataFrame)
        assert set(signals_df.columns) >= {'ts', 'symbol', 'score', 'signal', 'position_size'}
        assert len(signals_df) == 5
        
        # Check signal mapping is correct
        assert 'BUY' in signals_df['signal'].values
        assert 'SELL' in signals_df['signal'].values
        assert all(0 <= x <= 1 for x in signals_df['position_size'])
        
        # Verify file was written
        assert signals_path.exists()
        loaded_signals = pd.read_parquet(str(signals_path))
        pd.testing.assert_frame_equal(signals_df, loaded_signals)

def test_predict_signal_with_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "test_model.pkl"
        features_path = Path(tmpdir) / "test_features.parquet"
        signals_path = Path(tmpdir) / "test_signals.parquet"
        
        # Custom thresholds
        threshold_config = {
            'buy': 0.8,
            'sell': 0.3,
            'max_position': 0.5
        }
        
        # Setup mock data (same as above)
        model = MockModel()
        save_model(model, str(model_path))
        
        features_df = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [0.1, 0.2, 0.3, 0.4, 0.5],
            'symbol': ['BTC-USDT'] * 5
        }, index=pd.date_range('2024-01-01', periods=5, freq='1D'))
        features_df.to_parquet(str(features_path))
        
        # Run with custom config
        signals_df = predict_signals(
            model_path=str(model_path),
            features_path=str(features_path),
            output_path=str(signals_path),
            threshold_config=threshold_config
        )
        
        # Validate position sizes respect max_position
        assert all(x <= threshold_config['max_position'] for x in signals_df['position_size'])

def test_main_cli(tmp_path):
    """Test the CLI interface"""
    model_path = tmp_path / "test_model.pkl"
    features_path = tmp_path / "test_features.parquet"
    signals_path = tmp_path / "test_signals.parquet"
    config_path = tmp_path / "config.yaml"
    
    # Setup test data
    model = MockModel()
    save_model(model, str(model_path))
    
    features_df = pd.DataFrame({
        'feature1': [1, 2],
        'feature2': [0.1, 0.2],
        'symbol': ['BTC-USDT'] * 2
    }, index=pd.date_range('2024-01-01', periods=2, freq='1D'))
    features_df.to_parquet(str(features_path))
    
    # Create config file
    config = {'buy': 0.7, 'sell': 0.3, 'max_position': 0.5}
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    # Test CLI with arguments
    sys.argv = [
        'predict_and_signal.py',
        '--model-path', str(model_path),
        '--features-path', str(features_path),
        '--output-path', str(signals_path),
        '--config', str(config_path)
    ]
    
    main()
    
    # Verify output was created
    assert signals_path.exists()
    signals_df = pd.read_parquet(str(signals_path))
    assert set(signals_df.columns) >= {'ts', 'symbol', 'score', 'signal', 'position_size'}
