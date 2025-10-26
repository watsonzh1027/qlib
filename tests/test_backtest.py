import pytest
import pandas as pd
import numpy as np
from qlib.backtest.crypto import BacktestEngine
from datetime import datetime, timezone

@pytest.fixture
def sample_data():
    """Generate sample price and signal data"""
    dates = pd.date_range("2024-01-01", "2024-01-10", freq="15min", tz="UTC")
    
    # Create trending price series with some volatility
    prices = pd.DataFrame({
        'open': np.linspace(40000, 42000, len(dates)) + np.random.randn(len(dates)) * 100,
        'high': np.linspace(40100, 42100, len(dates)) + np.random.randn(len(dates)) * 100,
        'low': np.linspace(39900, 41900, len(dates)) + np.random.randn(len(dates)) * 100,
        'close': np.linspace(40000, 42000, len(dates)) + np.random.randn(len(dates)) * 100,
        'volume': np.random.random(len(dates)) * 1000
    }, index=dates)
    
    # Create some trading signals
    signals = pd.DataFrame({
        'signal': ['BUY', 'HOLD', 'SELL'] * (len(dates) // 3),
        'position_size': np.sin(np.linspace(0, 4*np.pi, len(dates))),  # Oscillating positions
        'score': np.random.random(len(dates))
    }, index=dates)
    
    return prices, signals

def test_backtest_execution(sample_data):
    """Test basic backtest execution"""
    prices, signals = sample_data
    engine = BacktestEngine()
    
    results = engine.run(prices, signals)
    
    # Verify results structure
    assert isinstance(results, dict)
    assert "equity_curve" in results
    assert "trades" in results
    assert "metrics" in results
    
    # Check metrics
    metrics = results["metrics"]
    assert "sharpe_ratio" in metrics
    assert "max_drawdown" in metrics
    assert "total_return" in metrics
    assert "win_rate" in metrics

def test_transaction_costs():
    """Test transaction cost calculation"""
    engine = BacktestEngine(fee_rate=0.001, slippage=0.001)  # 0.1% each
    
    # Create simple price series
    prices = pd.DataFrame({
        'open': [100] * 3,
        'close': [100] * 3
    }, index=pd.date_range("2024-01-01", "2024-01-03"))
    
    # Buy and sell signals
    signals = pd.DataFrame({
        'signal': ['BUY', 'HOLD', 'SELL'],
        'position_size': [1, 1, 0]
    }, index=prices.index)
    
    results = engine.run(prices, signals)
    
    # Should lose ~0.4% on round trip (0.2% each way)
    assert results["metrics"]["total_return"] < 0
    assert abs(results["metrics"]["total_return"] + 0.004) < 0.0001

def test_risk_metrics(sample_data):
    """Test risk metric calculations"""
    prices, signals = sample_data
    engine = BacktestEngine()
    
    results = engine.run(prices, signals)
    metrics = results["metrics"]
    
    # Verify risk metrics
    assert 0 <= metrics["win_rate"] <= 1
    assert metrics["max_drawdown"] <= 0
    assert isinstance(metrics["sharpe_ratio"], float)
    
    # Check drawdown calculation
    equity = results["equity_curve"]
    rolling_max = equity["equity"].expanding().max()
    drawdown = (equity["equity"] - rolling_max) / rolling_max
    assert abs(metrics["max_drawdown"] - drawdown.min()) < 0.0001

@pytest.mark.parametrize("position_size", [0.5, 1.0, 2.0])
def test_position_limits(sample_data, position_size):
    """Test position size limits"""
    prices, signals = sample_data
    engine = BacktestEngine(max_position=position_size)
    
    # Modify signals to test position limit
    signals["position_size"] = position_size * 1.5  # Try to exceed limit
    
    results = engine.run(prices, signals)
    
    # Check that positions never exceed limit
    positions = results["equity_curve"]["position"]
    assert positions.abs().max() <= position_size
