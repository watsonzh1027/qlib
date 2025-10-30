import pytest
from pathlib import Path
import pandas as pd
import json
import tempfile
import sys
import numpy as np
from unittest.mock import patch

from features.crypto_workflow.backtest_report import write_backtest_report


def test_write_backtest_report(tmp_path):
    """Test write_backtest_report function."""
    # Prepare test data
    backtest_result = {
        "metrics": {"sharpe": 1.5, "max_drawdown": 0.1},
        "trades": pd.DataFrame({
            "symbol": ["BTC", "ETH"],
            "price": [50000, 3000],
            "quantity": [1, 2]
        })
    }

    # Call the function
    write_backtest_report(backtest_result, tmp_path)

    # Verify outputs
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "trades.csv").exists()
    assert (tmp_path / "trades.parquet").exists()

    # Check content of metrics.json
    with open(tmp_path / "metrics.json", "r") as f:
        metrics = json.load(f)
    metrics.pop("generated_at", None)  # Remove the timestamp before comparison
    assert metrics == {"sharpe": 1.5, "max_drawdown": 0.1}

    # Check content of trades.csv
    trades = pd.read_csv(tmp_path / "trades.csv")
    assert trades.shape == (2, 3)
    assert list(trades.columns) == ["symbol", "price", "quantity"]


def test_backtest_report():
    """Test backtest report generation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)

        # Create sample backtest result
        dates = pd.date_range('2024-01-01', '2024-01-02', freq='1H')
        equity_curve = pd.DataFrame({
            'ts': dates,
            'equity': 1000 * (1 + np.random.randn(len(dates)).cumsum() * 0.01)
        })

        trades = pd.DataFrame({
            'ts': dates[::4][:6],
            'position': [0.5, -0.3, 0.4, -0.2, 0.1, 0.0],
            'trade': [0.5, -0.8, 0.7, -0.6, 0.3, -0.1],
            'pnl': [10, -5, 8, -3, 2, -1],
            'equity': [1010, 1005, 1013, 1010, 1012, 1011]
        })

        result = {
            'metrics': {
                'cumulative_return': 0.011,
                'max_drawdown': 0.008,
                'sharpe': 1.2,
                'periods': len(dates)
            },
            'equity_curve': equity_curve,
            'trades': trades
        }

        # Write report
        write_backtest_report(result, outdir)

        # Verify files
        assert (outdir / 'metrics.json').exists()
        assert (outdir / 'trades.csv').exists()
        assert (outdir / 'trades.parquet').exists()
        assert (outdir / 'equity_curve.csv').exists()
        assert (outdir / 'equity_curve.parquet').exists()
        assert (outdir / 'report.html').exists()

        # Verify metrics content
        with open(outdir / 'metrics.json') as f:
            metrics = json.load(f)
            assert 'cumulative_return' in metrics
            assert 'generated_at' in metrics

        # Verify data files
        loaded_trades = pd.read_parquet(outdir / 'trades.parquet')
        pd.testing.assert_frame_equal(loaded_trades, trades)

        loaded_eq = pd.read_parquet(outdir / 'equity_curve.parquet')
        pd.testing.assert_frame_equal(loaded_eq, equity_curve)


def test_backtest_report_empty():
    """Test report generation with empty results"""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)

        result = {
            'metrics': {'cumulative_return': 0.0},
            'equity_curve': pd.DataFrame(),
            'trades': pd.DataFrame()
        }

        write_backtest_report(result, outdir)
        assert (outdir / 'metrics.json').exists()

def test_html_report_generation_failure(tmp_path):
    """Test that a warning is logged if HTML report generation fails."""
    with patch('features.crypto_workflow.backtest_report.create_html_report', side_effect=Exception("Test exception")):
        backtest_result = {
            "metrics": {"sharpe": 1.5, "max_drawdown": 0.1},
            "equity_curve": pd.DataFrame({'ts': [1], 'equity': [1]})
        }
        write_backtest_report(backtest_result, tmp_path)
        # We can't easily check the log output here without more setup,
        # but we can verify that the function doesn't crash and that other files are created.
        assert (tmp_path / "metrics.json").exists()