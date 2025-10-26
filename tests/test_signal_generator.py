import json
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from qlib.signals.crypto import SignalGenerator

@pytest.fixture
def mock_predictions():
    """Generate mock model predictions"""
    dates = pd.date_range("2024-01-01", "2024-01-02", freq="15min", tz="UTC")
    return pd.Series(
        np.random.random(len(dates)),  # Random scores between 0 and 1
        index=dates
    )

def test_signal_generation(mock_predictions):
    """Test basic signal generation from model scores"""
    generator = SignalGenerator()
    signals = generator.generate(mock_predictions)
    
    # Verify signal properties
    assert isinstance(signals, pd.DataFrame)
    assert len(signals) == len(mock_predictions)
    assert all(col in signals.columns for col in ["signal", "score", "position_size"])
    assert signals["signal"].isin(["BUY", "SELL", "HOLD"]).all()
    assert (signals["position_size"] >= 0).all() and (signals["position_size"] <= 1).all()

def test_signal_thresholds():
    """Test signal thresholds according to config"""
    generator = SignalGenerator()
    
    # Test specific scores
    test_cases = pd.Series({
        pd.Timestamp("2024-01-01"): 0.8,  # Should be BUY
        pd.Timestamp("2024-01-02"): 0.2,  # Should be SELL
        pd.Timestamp("2024-01-03"): 0.5,  # Should be HOLD
    })
    
    signals = generator.generate(test_cases)
    assert signals.loc[signals["score"] == 0.8, "signal"].iloc[0] == "BUY"
    assert signals.loc[signals["score"] == 0.2, "signal"].iloc[0] == "SELL"
    assert signals.loc[signals["score"] == 0.5, "signal"].iloc[0] == "HOLD"

def test_position_sizing():
    """Test position size calculation"""
    generator = SignalGenerator()

    # Test extreme scores
    test_cases = pd.Series({
        pd.Timestamp("2024-01-01"): 1.0,  # Maximum buy
        pd.Timestamp("2024-01-02"): 0.0,  # Maximum sell
        pd.Timestamp("2024-01-03"): 0.5,  # Neutral
    })

    signals = generator.generate(test_cases)
    assert signals.loc[signals["score"] == 1.0, "position_size"].iloc[0] == 1.0
    assert signals.loc[signals["score"] == 0.0, "position_size"].iloc[0] == 0.01
    assert signals.loc[signals["score"] == 0.5, "position_size"].iloc[0] == 0.5

def test_save_signals(tmp_path):
    """Test saving signals to file with metadata"""
    generator = SignalGenerator()

    # Generate test signals
    test_cases = pd.Series({
        pd.Timestamp("2024-01-01"): 0.8,
        pd.Timestamp("2024-01-02"): 0.2,
    })
    signals = generator.generate(test_cases)

    # Save signals
    signal_path = tmp_path / "test_signals.csv"
    generator.save_signals(signals, signal_path)

    # Verify CSV file exists and contains data
    assert signal_path.exists()
    saved_signals = pd.read_csv(signal_path, index_col=0, parse_dates=True)
    pd.testing.assert_frame_equal(signals, saved_signals)

    # Verify metadata file exists and contains correct data
    meta_path = signal_path.with_suffix(".json")
    assert meta_path.exists()
    with open(meta_path) as f:
        meta = json.load(f)

    assert "generated_at" in meta
    assert "thresholds" in meta
    assert "position_limits" in meta
    assert meta["thresholds"] == generator.config["thresholds"]
    assert meta["position_limits"] == generator.config["position"]
