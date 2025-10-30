#!/usr/bin/env python3
"""
Simple backtest harness:
- Input: signals parquet (ts,symbol,score,signal,position_size) and OHLCV parquet (timestamp,indexed)
- Output: metrics JSON and trades CSV/parquet via backtest_report
"""
import argparse
from pathlib import Path
import json
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from features.crypto_workflow.backtest_report import write_backtest_report
logger = logging.getLogger(__name__)

class Backtester:
    def __init__(self, slippage: float = 0.0005, fee: float = 0.00075, init_capital: float = 1.0):
        self.slippage = slippage
        self.fee = fee
        self.init_capital = init_capital

    def _prepare(self, signals: pd.DataFrame, ohlcv: pd.DataFrame) -> pd.DataFrame:
        # Ensure timestamp index and columns
        df_signals = signals.copy()
        if 'ts' not in df_signals.columns:
            raise ValueError("Signals DataFrame must contain 'ts' column")
        df_signals = df_signals.set_index(pd.to_datetime(df_signals['ts']))
        df_signals.index.name = 'timestamp'
        ohlcv_indexed = ohlcv.copy()
        if not isinstance(ohlcv_indexed.index, pd.DatetimeIndex):
            if 'timestamp' in ohlcv_indexed.columns:
                ohlcv_indexed = ohlcv_indexed.set_index(pd.to_datetime(ohlcv_indexed['timestamp']), drop=True)
        ohlcv_indexed = ohlcv_indexed.sort_index()
        # Align signals to OHLCV timestamps (forward fill latest signal)
        merged = ohlcv_indexed.merge(df_signals[['signal','position_size']], how='left', left_index=True, right_index=True)
        merged[['signal','position_size']] = merged[['signal','position_size']].ffill().fillna({'signal':'HOLD','position_size':0})
        return merged

    def run(self, signals: pd.DataFrame, ohlcv: pd.DataFrame, output_dir=None):
        df = self._prepare(signals, ohlcv)
        df = df.assign(
            position=0.0,
            trade=0.0,
            pnl=0.0,
            equity=0.0
        )

        prev_pos = 0.0
        equity = self.init_capital
        df.iloc[0, df.columns.get_loc('equity')] = equity
        returns = []

        close = df['close']
        # compute period returns
        pct = close.pct_change().fillna(0.0)

        for i, (ts, row) in enumerate(df.iterrows()):
            desired_size = 0.0
            sig = row.get('signal', 'HOLD')
            size = row.get('position_size', 0.0) or 0.0
            if sig == 'BUY':
                desired_size = float(size)
            elif sig == 'SELL':
                desired_size = -float(size)
            else:
                desired_size = 0.0

            # portfolio return = prev position * pct_return
            port_ret = prev_pos * pct.iloc[i]
            # trading costs when changing position
            trade_amount = abs(desired_size - prev_pos)
            trade_cost = trade_amount * self.fee
            slip_cost = trade_amount * self.slippage

            equity = equity * (1.0 + port_ret) - trade_cost - slip_cost
            df.at[ts, 'position'] = desired_size
            df.at[ts, 'trade'] = desired_size - prev_pos
            df.at[ts, 'pnl'] = port_ret * self.init_capital
            df.at[ts, 'equity'] = equity
            returns.append(port_ret)

            prev_pos = desired_size

        # metrics
        returns_arr = np.array(returns)
        cumulative_return = equity / self.init_capital - 1.0
        peak = np.maximum.accumulate(df['equity'].values)
        drawdown = (peak - df['equity'].values) / peak
        max_drawdown = float(np.nanmax(drawdown)) if len(drawdown) else 0.0
        # annualize assuming daily frequency if index daily else use 252
        ann_factor = 252.0
        if len(returns_arr) > 1:
            avg = returns_arr.mean()
            vol = returns_arr.std(ddof=1)
            sharpe = float((avg / vol) * np.sqrt(ann_factor)) if vol > 0 else 0.0
            ann_return = float(np.prod(1 + returns_arr) ** (ann_factor / max(1, len(returns_arr))) - 1.0)
        else:
            sharpe = 0.0
            ann_return = 0.0

        metrics = {
            'cumulative_return': float(cumulative_return),
            'annualized_return': ann_return,
            'max_drawdown': max_drawdown,
            'sharpe': sharpe,
            'final_equity': float(equity),
            'periods': int(len(returns_arr))
        }

        # extract trades
        trades = df[df['trade'] != 0.0][['position','trade','pnl','equity']]
        trades = trades.reset_index().rename(columns={'index':'ts'})

        # Ensure 'ts' column exists in equity_curve
        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index().rename(columns={'index': 'ts'})
        else:
            df = df.reset_index().rename(columns={'timestamp': 'ts'})

        result = {
            'metrics': metrics,
            'equity_curve': df[['equity', 'ts']],
            'trades': trades,
            'detailed': df
        }

        # Save metrics to file if output_dir is provided
        if output_dir:
            import os
            import json
            from pathlib import Path
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            metrics_path = output_path / "metrics.json"
            try:
                with open(metrics_path, "w") as f:
                    json.dump(metrics, f, indent=4)
                print(f"Metrics saved to {metrics_path}")
                assert os.path.exists(metrics_path), f"Failed to create {metrics_path}"
                # Also save trades if not empty
                if not trades.empty:
                    trades_path = output_path / "trades.csv"
                    trades.to_csv(trades_path, index=False)
            except Exception as e:
                print(f"Failed to save metrics: {e}")
                raise

        return result

def run_backtest(signals_path: str, ohlcv_path: str, output_path: str, slippage: float = 0.0005, fee: float = 0.00075):
    # read signals and ohlcv data, supporting both parquet and csv
    if signals_path.endswith('.parquet'):
        signals = pd.read_parquet(signals_path)
    else:
        signals = pd.read_csv(signals_path, parse_dates=['ts'])
    
    if ohlcv_path.endswith('.parquet'):
        ohlcv = pd.read_parquet(ohlcv_path)
    else:
        ohlcv = pd.read_csv(ohlcv_path, parse_dates=['timestamp'])

    bt = Backtester(slippage=slippage, fee=fee)
    result = bt.run(signals=signals, ohlcv=ohlcv, output_dir=output_path)
    write_backtest_report(result, Path(output_path))
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--signals', required=True, help='Path to signals parquet/csv')
    parser.add_argument('--ohlcv', required=True, help='Path to ohlcv parquet/csv (indexed by timestamp/with timestamp col)')
    parser.add_argument('--output', required=True, help='Output report base path (dir will be created)')
    parser.add_argument('--slippage', type=float, default=0.0005)
    parser.add_argument('--fee', type=float, default=0.00075)
    args = parser.parse_args()

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    run_backtest(args.signals, args.ohlcv, str(outdir), slippage=args.slippage, fee=args.fee)

if __name__ == '__main__':
    main()
