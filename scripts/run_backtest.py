import sys
import os
import json
import argparse
import pandas as pd
import pickle
from pathlib import Path
import qlib
from qlib.config import REG_CN
from qlib.utils import init_instance_by_config
from qlib.data.dataset import DatasetH
from qlib.backtest import backtest, executor as executor_module
from qlib.contrib.report import analysis_model, analysis_position
from qlib.contrib.strategy import CryptoLongShortStrategy
from qlib.utils.logging_config import setup_logging

# Configure logging
logger = setup_logging()

# Add mapping logic (duplicate)
def map_symbol(symbol):
    symbol = symbol.upper()
    if "_" not in symbol:
        if symbol.endswith("USDT"):
            coin = symbol[:-4]
            return f"{coin}_USDT_4H_FUTURE"
    return symbol

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    args, unknown = parser.parse_known_args()

    config_path = Path(args.config)
    with open(config_path, "r") as f:
        config = json.load(f)

    provider_uri = config.get("data", {}).get("bin_data_dir", "data/qlib_data/crypto")
    qlib.init(provider_uri=provider_uri, region=REG_CN)

    # Load Model
    model_path = Path("tmp/tuning") / f"{config_path.stem}.pkl"
    if not model_path.exists():
        print("Model file not found!")
        sys.exit(1)
        
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    # Prepare Dataset for Test
    raw_symbols = config.get("training", {}).get("instruments", [])
    instruments = [map_symbol(s) for s in raw_symbols]
    
    # Dataset just for prediction (Test Segment)
    dh_config = {
        "start_time": args.start,
        "end_time": args.end,
        "instruments": instruments,
        "infer_processors": [],
        "learn_processors": [],
        "freq": "240min"
    }
    
    # Load handler config
    dh_cfg_from_json = config.get("data_handler_config", {})
    handler_class = dh_cfg_from_json.get("class", "Alpha158")
    module_path = dh_cfg_from_json.get("module_path", "qlib.contrib.data.handler")

    dataset_config = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": {
                "class": handler_class,
                "module_path": module_path,
                "kwargs": dh_config
            },
            "segments": {
                "test": (args.start, args.end),
            }
        }
    }
    dataset = init_instance_by_config(dataset_config)
    
    # Predict
    pred = model.predict(dataset)
    if isinstance(pred, pd.DataFrame):
        pred = pred.iloc[:, 0]
        
    # Prepare Strategy
    trading_cfg = config.get("trading", {})
    backtest_cfg = config.get("backtest", {})
    
    # Map 'threshold' -> 'signal_threshold'
    signal_thresh = trading_cfg.get("signal_threshold", 0.0)
    
    # Prepare Strategy configuration moves down
    
    strategy_config = {
        "class": "CryptoLongShortStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {
            "signal": pred,
            "signal_threshold": signal_thresh,
            "leverage": trading_cfg.get("leverage", 1.0),
            "topk": backtest_cfg.get("topk", 1),
            "stop_loss": trading_cfg.get("stop_loss", -0.05),
            "take_profit": trading_cfg.get("take_profit", 0.1),
            "direction": "long-short",
            "target_symbols": instruments # Important for the strategy!
        }
    }

    # Prepare Executor
    executor_config = {
        "class": "SimulatorExecutor",
        "module_path": "qlib.backtest.executor",
        "kwargs": {
            "time_per_step": "240min",
            "generate_portfolio_metrics": True,
            "verbose": True
        }
    }

    # Run Backtest
    # Need to construct Backtest Config
    # exchange_kwargs
    exchange_kwargs = {
        "freq": "240min",
        "start_time": args.start,
        "end_time": args.end,
        "limit_threshold": None,
        "deal_price": "close",
        "open_cost": 0.0001,
        "close_cost": 0.0001,
        "min_cost": 0.0,
        "trade_unit": None
    }

    exchange_kwargs["codes"] = list(pred.index.get_level_values("instrument").unique())

    portfolio_metric_dict, indicator_dict = backtest(
        start_time=args.start,
        end_time=args.end,
        strategy=strategy_config,
        executor=executor_config,
        exchange_kwargs=exchange_kwargs,
        account=1000000,
        benchmark=None,
    )

    # Analysis
    # We need to print metrics for `tune_hyperparameters.py` to parse.
    # Metrics: Sharpe Ratio, Annualized Return, Max Drawdown
    
    # portfolio_metric_dict contains return, cost, turnover etc.
    # But usually we need `analysis_model.metrics`.
    
    # However, `backtest` returns (portfolio_metrics, indicator_metrics)
    # portfolio_metrics is a DataFrame of daily/step metrics.
    # We can calculate Sharpe from it.
    
    # Actually, let's use `qlib.contrib.evaluate.risk_analysis` if available, or just manual calculation.
    # `portfolio_metric_dict` is the raw metrics dataframe.
    
    metrics_df = portfolio_metric_dict
    
    # Handle dict return from backtest (keyed by frequency)
    if isinstance(metrics_df, dict):
        if "240min" in metrics_df:
            metrics_df = metrics_df["240min"]
        elif "1day" in metrics_df:
            metrics_df = metrics_df["1day"]
        elif len(metrics_df) > 0:
            # Fallback: take first value
            metrics_df = list(metrics_df.values())[0]
            
    # Handle case where value is tuple (metrics, indicators)
    if isinstance(metrics_df, tuple):
        metrics_df = metrics_df[0]
            
    # Calculate Sharpe
    # returns are in 'return' column?
    # Actually SimulatorExecutor returns DataFrame with columns like 'return', 'cost', 'bench', 'turnover'.
    
    # Simple calculation
    returns = metrics_df["return"]
    
    if returns.empty or returns.std() == 0:
         sharpe = 0
         ann_ret = 0
         mdd = 0
         win_rate = 0
    else:
        # Annualize factor for 4h (6 steps/day * 365) = 2190
        ann_scaler = 2190
        # Wait, if `time_per_step` is 240min, `returns` are per 4h.
        
        sharpe = returns.mean() / returns.std() * (ann_scaler ** 0.5)
        ann_ret = returns.mean() * ann_scaler
        
        # Max Drawdown
        cum_ret = (1 + returns).cumprod()
        peak = cum_ret.cummax()
        drawdown = (cum_ret - peak) / peak
        mdd = abs(drawdown.min())
        
        win_rate = (returns > 0).mean()
        
    # Print in format expected by parsing regex
    # Sharpe Ratio: 1.5
    # Annualized Return: 20.5%
    # Max Drawdown: 10.2%
    # Win Rate: 55.0%
    # Total Trades: ... (Hard to get exactly from metrics DF without transaction log, but tuner parses it if present)
    
    print(f"Sharpe Ratio: {sharpe:.4f}")
    print(f"Annualized Return: {ann_ret*100:.2f}%")
    print(f"Max Drawdown: {mdd*100:.2f}%")
    print(f"Win Rate: {win_rate*100:.2f}%")

    # Calculate Total Trades based on turnover
    # Turnover > 0 implies trading activity occurred
    if "turnover" in metrics_df.columns:
        total_trades = (metrics_df["turnover"] > 1e-6).sum()
    else:
        total_trades = 0
    print(f"Total Trades: {total_trades}")

if __name__ == "__main__":
    main()
