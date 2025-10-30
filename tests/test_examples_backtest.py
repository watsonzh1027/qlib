import pytest
from pathlib import Path
import pandas as pd
import numpy as np

from examples.backtest import run_backtest


def test_run_backtest(tmp_path):
    """Test run_backtest function with Parquet files."""
    # Prepare test data
    signals = pd.DataFrame({
        "ts": pd.to_datetime(["2023-01-01", "2023-01-02"]),
        "symbol": ["BTC", "ETH"],
        "score": [0.8, 0.6],
        "signal": ["BUY", "SELL"],
        "position_size": [0.5, 0.3]
    })
    ohlcv = pd.DataFrame({
        "timestamp": pd.to_datetime(["2023-01-01", "2023-01-02"]),
        "symbol": ["BTC", "ETH"],
        "open": [50000, 3000],
        "high": [51000, 3100],
        "low": [49000, 2900],
        "close": [50500, 3050],
        "volume": [1000, 2000]
    })

    # Save test data to files
    signals_path = tmp_path / "signals.parquet"
    ohlcv_path = tmp_path / "ohlcv.parquet"
    signals.to_parquet(signals_path)
    ohlcv.to_parquet(ohlcv_path)

    # Call the function
    result = run_backtest(str(signals_path), str(ohlcv_path), tmp_path)


def test_run_backtest_csv(tmp_path):
    """Test run_backtest function with CSV files."""
    # Prepare test data
    signals = pd.DataFrame({
        "ts": ["2023-01-01", "2023-01-02"],
        "symbol": ["BTC", "ETH"],
        "score": [0.8, 0.6],
        "signal": ["BUY", "SELL"],
        "position_size": [0.5, 0.3]
    })
    ohlcv = pd.DataFrame({
        "timestamp": ["2023-01-01", "2023-01-02"],
        "symbol": ["BTC", "ETH"],
        "open": [50000, 3000],
        "high": [51000, 3100],
        "low": [49000, 2900],
        "close": [50500, 3050],
        "volume": [1000, 2000]
    })

    # Save test data to files
    signals_path = tmp_path / "signals.csv"
    ohlcv_path = tmp_path / "ohlcv.csv"
    signals.to_csv(signals_path, index=False)
    ohlcv.to_csv(ohlcv_path, index=False)

    # Call the function
    result = run_backtest(str(signals_path), str(ohlcv_path), tmp_path)


def test_prepare_method(tmp_path):
    """Test _prepare method with different input formats."""
    from examples.backtest import Backtester

    # Case 1: signals with 'ts' column
    signals = pd.DataFrame({
        "ts": ["2023-01-01", "2023-01-02"],
        "symbol": ["BTC", "ETH"],
        "signal": ["BUY", "SELL"],
        "position_size": [0.5, 0.3]
    })
    ohlcv = pd.DataFrame({
        "timestamp": ["2023-01-01", "2023-01-02"],
        "symbol": ["BTC", "ETH"],
        "close": [50500, 3050]
    })

    bt = Backtester()
    prepared = bt._prepare(signals, ohlcv)
    assert isinstance(prepared.index, pd.DatetimeIndex)

    # Case 2: signals without 'ts' column (should raise error)
    signals_no_ts = signals.drop(columns=['ts'])
    try:
        bt._prepare(signals_no_ts, ohlcv)
        assert False, "Expected ValueError"
    except ValueError:
        pass

    # Case 3: ohlcv without timestamp index
    ohlcv_no_index = ohlcv.reset_index(drop=True)
    prepared = bt._prepare(signals, ohlcv_no_index)
    assert isinstance(prepared.index, pd.DatetimeIndex)


def test_run_method(tmp_path):
    """Test run method with different signal types."""
    from examples.backtest import Backtester

    # Prepare test data
    signals = pd.DataFrame({
        "ts": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "symbol": ["BTC", "ETH", "BTC"],
        "signal": ["BUY", "SELL", "HOLD"],
        "position_size": [0.5, 0.3, 0.0]
    })
    ohlcv = pd.DataFrame({
        "timestamp": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "symbol": ["BTC", "ETH", "BTC"],
        "close": [50500, 3050, 51000]
    })

    bt = Backtester()
    result = bt.run(signals, ohlcv, output_dir=str(tmp_path))

    # Verify BUY and SELL signals are processed
    assert 'equity_curve' in result
    assert 'trades' in result
    assert len(result['trades']) >= 2  # Expect at least 2 trades (BUY and SELL)

    # Verify outputs
    assert isinstance(result, dict)
    assert "metrics" in result
    assert "trades" in result
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "trades.csv").exists()