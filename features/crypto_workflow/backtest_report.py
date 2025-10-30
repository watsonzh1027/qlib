import json
from pathlib import Path
import pandas as pd

def write_backtest_report(backtest_result: dict, outdir: Path):
    """Serialize backtest metrics, trades and equity curve to outdir"""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Metrics
    metrics = backtest_result.get('metrics', {})
    with open(outdir / 'metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    # Trades
    trades = backtest_result.get('trades')
    if trades is not None and not trades.empty:
        trades.to_csv(outdir / 'trades.csv', index=False)
        trades.to_parquet(outdir / 'trades.parquet', index=False)

    # Equity curve
    eq = backtest_result.get('equity_curve')
    if eq is not None and not eq.empty:
        eq.to_parquet(outdir / 'equity_curve.parquet', index=False)
        eq.to_csv(outdir / 'equity_curve.csv', index=False)

    # Full detailed dataframe optional
    detailed = backtest_result.get('detailed')
    if detailed is not None:
        detailed.to_parquet(outdir / 'detailed.parquet', index=False)
