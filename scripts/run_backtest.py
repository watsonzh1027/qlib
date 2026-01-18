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

from qlib.utils.logging_config import startlog, endlog

# Configure logging
logger = startlog("run_backtest")

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Add mapping logic (duplicate)
def map_symbol(symbol):
    symbol = symbol.upper()
    if "/" in symbol:
        return symbol.split("/")[0]
    if "_" not in symbol and symbol.endswith("USDT"):
        return f"{symbol[:-4]}_USDT"
    return symbol

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    args, unknown = parser.parse_known_args()

    # config_path = Path(args.config)
    # with open(config_path, "r") as f:
    #     config = json.load(f)

    from scripts.config_manager import ConfigManager
    cm = ConfigManager(args.config)
    config = cm.config
    
    # Overwrite with resolved
    config["data_handler_config"] = cm.get_data_handler_config()
    config["dataset"] = cm.get_dataset_config()
    config["backtest"] = cm.get_backtest_config() # Important for backtest params
    config["port_analysis"] = cm.get_port_analysis_config()
    
    config_path = Path(args.config) # Keep for model path logic below

    provider_uri = config.get("data", {}).get("bin_data_dir", "data/qlib_data/crypto")
    qlib.init(provider_uri=provider_uri, region=REG_CN)
    
    # Get freq from resolved workflow config
    raw_freq = cm.get_workflow_config()["frequency"]
    if not raw_freq:
         raw_freq = config.get("data_collection", {}).get("interval", "60min")

    # Load Model
    model_path = Path("tmp/tuning") / f"{config_path.stem}.pkl"
    if not model_path.exists():
        print("Model file not found!")
        sys.exit(1)
        
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    # Prepare Dataset for Test
    # Prepare Dataset for Test
    raw_symbols = config.get("training", {}).get("instruments", [])
    if not raw_symbols:
        dh_cfg = cm.get_data_handler_config()
        if "kwargs" in dh_cfg and "instruments" in dh_cfg["kwargs"]:
            raw_symbols = dh_cfg["kwargs"]["instruments"]
        elif "instruments" in dh_cfg:
            raw_symbols = dh_cfg["instruments"]

    instruments = [map_symbol(s) for s in raw_symbols]
    
    # Dataset just for prediction (Test Segment)
    dh_config = {
        "start_time": args.start,
        "end_time": args.end,
        "instruments": instruments,
        "infer_processors": [],
        "learn_processors": [],
        "freq": raw_freq
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
    if "strategy" in config:
        # Use top-level strategy config if available (user preference)
        raw_strategy_cfg = config["strategy"]
    else:
        # Fallback to port_analysis strategy
        raw_strategy_cfg = config.get("port_analysis", {}).get("strategy", {})

    # Adapt flat structure to standard Qlib config (class, module_path, kwargs)
    # The user's top-level config is flat, Qlib expects kwargs
    strategy_config = {
        "class": raw_strategy_cfg.get("class", "CryptoLongShortStrategy"),
        "module_path": raw_strategy_cfg.get("module_path", "qlib.contrib.strategy"),
        "kwargs": {}
    }
    
    # If the config already has kwargs, start with that. Otherwise, use the whole dict as kwargs source
    source_kwargs = raw_strategy_cfg.get("kwargs", raw_strategy_cfg)
    
    # Copy all params that are NOT class/module_path/kwargs into the new kwargs
    for k, v in source_kwargs.items():
        if k not in ["class", "module_path", "kwargs"]:
            strategy_config["kwargs"][k] = v
            
    # Inject dynamic parameters
    strategy_config["kwargs"]["signal"] = pred
    # strategy_config["kwargs"]["target_symbols"] = instruments # Not strictly needed if signal covers it, but good for safety
    
    # Prepare Executor
    raw_executor_cfg = config.get("port_analysis", {}).get("executor", {})
    executor_config = {
        "class": raw_executor_cfg.get("class", "SimulatorExecutor"),
        "module_path": raw_executor_cfg.get("module_path", "qlib.backtest.executor"),
        "kwargs": raw_executor_cfg.get("kwargs", {})
    }
    # Ensure time_per_step matches runtime freq
    executor_config["kwargs"]["time_per_step"] = raw_freq
    executor_config["kwargs"]["generate_portfolio_metrics"] = True
    executor_config["kwargs"]["verbose"] = True

    # Run Backtest
    # Need to construct Backtest Config
    raw_exchange_kwargs = config.get("backtest", {}).get("exchange_kwargs", {})
    
    exchange_kwargs = raw_exchange_kwargs.copy()
    
    # Override with runtime args
    exchange_kwargs.update({
        "freq": raw_freq,
        "start_time": args.start,
        "end_time": args.end,
    })

    if "codes" not in exchange_kwargs:
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
    metrics_df = portfolio_metric_dict
    
    # Handle dict return from backtest (keyed by frequency)
    if isinstance(metrics_df, dict):
        if raw_freq in metrics_df:
            metrics_df = metrics_df[raw_freq]
        elif "1day" in metrics_df:
            metrics_df = metrics_df["1day"]
        elif len(metrics_df) > 0:
            # Fallback: take first value
            metrics_df = list(metrics_df.values())[0]
            
    # Handle case where value is tuple (metrics, indicators)
    if isinstance(metrics_df, tuple):
        metrics_df = metrics_df[0]
            
    # Calculate Sharpe
    returns = metrics_df["return"]
    
    if returns.empty or returns.std() == 0:
         sharpe = 0
         ann_ret = 0
         mdd = 0
         win_rate = 0
    else:
        # Calculate annular scaler based on freq
        if "min" in raw_freq:
            mins = int(raw_freq.replace("min", ""))
            ann_scaler = (60 / mins) * 24 * 365
        elif "h" in raw_freq:
             hours = int(raw_freq.replace("h", ""))
             ann_scaler = (24 / hours) * 365
        elif "d" in raw_freq:
            ann_scaler = 252 # traditional markets or 365 for crypto
        else:
            ann_scaler = 252 # Default
            
        sharpe = returns.mean() / returns.std() * (ann_scaler ** 0.5)
        ann_ret = returns.mean() * ann_scaler
        
        # Max Drawdown
        cum_ret = (1 + returns).cumprod()
        peak = cum_ret.cummax()
        drawdown = (cum_ret - peak) / peak
        mdd = abs(drawdown.min())
        
        win_rate = (returns > 0).mean()
        
    print(f"Sharpe Ratio: {sharpe:.4f}")
    print(f"Annualized Return: {ann_ret*100:.2f}%")
    print(f"Max Drawdown: {mdd*100:.2f}%")
    print(f"Win Rate: {win_rate*100:.2f}%")

    # Calculate Total Trades based on turnover
    if "turnover" in metrics_df.columns:
        total_trades = (metrics_df["turnover"] > 1e-6).sum()
    else:
        total_trades = 0
    print(f"Total Trades: {total_trades}")
    endlog(logger, "run_backtest")

if __name__ == "__main__":
    main()
