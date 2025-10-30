import pytest
from pathlib import Path
import pandas as pd
import json

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
    assert metrics == {"sharpe": 1.5, "max_drawdown": 0.1}

    # Check content of trades.csv
    trades = pd.read_csv(tmp_path / "trades.csv")
    assert trades.shape == (2, 3)
    assert list(trades.columns) == ["symbol", "price", "quantity"]