import qlib
import json
import pandas as pd
import numpy as np
from qlib.config import REG_CN
from qlib.utils import init_instance_by_config
from qlib.backtest import backtest
from pathlib import Path
import os
import sys

def main():
    best_cfg_path = Path("config/workflow.best.json")
    if not best_cfg_path.exists():
        print("Best config not found!")
        return

    with open(best_cfg_path, "r") as f:
        config = json.load(f)

    # 1. Init Qlib
    provider_uri = config.get("data", {}).get("bin_data_dir", "data/qlib_data/crypto")
    qlib.init(provider_uri=provider_uri, region=REG_CN)

    # 2. Get Best Params for ETH
    symbol = "ETH_USDT_4H_FUTURE"
    q_symbol = symbol
    if symbol not in config["per_symbol_models"]:
        # Fallback for old key
        if "ETHUSDT" in config["per_symbol_models"]:
            best_params = config["per_symbol_models"]["ETHUSDT"]
        else:
            print(f"Symbol {symbol} not found in best config!")
            return
    else:
        best_params = config["per_symbol_models"][symbol]
    
    print(f"Running Full Backtest for {symbol} with best params...")
    print(f"Signal Threshold: {best_params['trading']['signal_threshold']:.6f}")
    print(f"Min Sigma Threshold: {best_params['trading'].get('min_sigma_threshold', 0.0):.4f}")
    print(f"SL/TP: {best_params['trading']['stop_loss']:.4f} / {best_params['trading']['take_profit']:.4f}")

    # 3. Setup Dataset
    dh_config = config["data_handler_config"]["kwargs"].copy()
    dh_config["instruments"] = [q_symbol]
    dh_config["freq"] = "240min"
    # Ensure times are concrete
    dh_config["start_time"] = "2023-01-01"
    dh_config["end_time"] = "2025-12-31"
    dh_config["fit_start_time"] = "2023-01-01"
    dh_config["fit_end_time"] = "2023-12-31"

    dataset_config = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": {
                "class": config["data_handler_config"]["class"],
                "module_path": config["data_handler_config"]["module_path"],
                "kwargs": dh_config
            },
            "segments": {
                "train": ("2023-01-01", "2023-12-31"),
                "test": ("2024-01-01", "2025-12-31") # Extended test period
            }
        }
    }
    dataset = init_instance_by_config(dataset_config)

    # 4. Setup Model
    model_config = {
        "class": "LGBModel",
        "module_path": "qlib.contrib.model.gbdt",
        "kwargs": {
            "loss": "mse",
            "num_threads": 4,
            **best_params["model_params"]
        }
    }
    model = init_instance_by_config(model_config)

    # 5. Train
    print("Training...")
    model.fit(dataset)

    # 6. Predict
    print("Predicting...")
    pred = model.predict(dataset)
    if isinstance(pred, pd.DataFrame):
        pred = pred.iloc[:, 0]

    def ensure_index_format(s):
        # Qlib strategy expects: Level 0 = instrument, Level 1 = datetime
        if not isinstance(s.index, pd.MultiIndex):
            return s
        
        # Check if first level is datetime
        if isinstance(s.index.get_level_values(0)[0], (pd.Timestamp, np.datetime64)):
            print("SWAPPING INDEX LEVELS: Detected (datetime, instrument) order.")
            s = s.swaplevel(0, 1)
        
        s.index.names = ['instrument', 'datetime']
        return s.sort_index()

    pred = ensure_index_format(pred)
    
    thresh = best_params["trading"]["signal_threshold"]
    with open("tmp/debug_pred.txt", "w") as f:
        f.write(f"Signal Stats | Min: {pred.min():.6f}, Max: {pred.max():.6f}, Mean: {pred.mean():.6f}, Std: {pred.std():.6f}\n")
        f.write(f"Index Names: {pred.index.names}\n")
        f.write(f"Index Level 0 (Symbol) Unique: {pred.index.get_level_values(0).unique().tolist()}\n")
        f.write(f"Sample Predictions:\n{pred.head(20).to_string()}\n")
    
    print(f"DEBUG: Index fixed. Saved stats to tmp/debug_pred.txt")

    # 7. Strategy
    actual_symbols = pred.index.get_level_values(0).unique().tolist()
    print(f"DEBUG: Actual Symbols in Pred: {actual_symbols}")
    
    strategy_config = {
        "class": "CryptoLongShortStrategy",
        "module_path": "qlib.contrib.strategy.crypto_strategy",
        "kwargs": {
            "signal": pred,
            "signal_threshold": thresh,
            "min_sigma_threshold": best_params["trading"].get("min_sigma_threshold", 0.0),
            "leverage": best_params["trading"]["leverage"],
            "stop_loss": best_params["trading"]["stop_loss"],
            "take_profit": best_params["trading"]["take_profit"],
            "topk": best_params["backtest_topk"],
            "direction": "long-short",
            "target_symbols": actual_symbols, # Use actual names from pred
            "risk_degree": 0.95,
        }
    }

    # 8. Executor
    executor_config = {
        "class": "SimulatorExecutor",
        "module_path": "qlib.backtest.executor",
        "kwargs": {
            "time_per_step": "240min",
            "generate_portfolio_metrics": True,
            "verbose": False
        }
    }

    # 9. Run
    print("Backtesting...")
    portfolio_metric_dict, indicator_dict = backtest(
        start_time="2024-01-01",
        end_time="2025-06-01",
        strategy=strategy_config,
        executor=executor_config,
        exchange_kwargs={
            "codes": [q_symbol],
            "freq": "240min",
            "limit_threshold": None,
            "deal_price": "close",
            "open_cost": 0.0005,
            "close_cost": 0.0005
        },
        account=1000000,
        benchmark=None
    )

    # 10. Report
    metrics_df = portfolio_metric_dict
    
    # Handle dict return from backtest (keyed by frequency)
    if isinstance(metrics_df, dict):
        if "240min" in metrics_df:
            metrics_df = metrics_df["240min"]
        elif "1day" in metrics_df:
            metrics_df = metrics_df["1day"]
        elif len(metrics_df) > 0:
            metrics_df = list(metrics_df.values())[0]
            
    # Handle case where value is tuple (metrics, indicators)
    if isinstance(metrics_df, tuple):
        metrics_df = metrics_df[0]

    returns = metrics_df["return"]
    sharpe = returns.mean() / returns.std() * (2190 ** 0.5)
    ann_ret = returns.mean() * 2190
    
    cum_ret = (1 + returns).cumprod()
    mdd = (cum_ret / cum_ret.cummax() - 1).min()

    print("\n" + "="*40)
    print(f"FINAL PERFORMANCE REPORT: {symbol}")
    print("="*40)
    print(f"Sharpe Ratio:      {sharpe:.4f}")
    print(f"Annualized Return: {ann_ret*100:.2f}%")
    print(f"Max Drawdown:      {mdd*100:.2f}%")
    print(f"Win Rate:          {(returns > 0).mean()*100:.2f}%")
    print("="*40)

    # Save to file
    with open("tmp/final_backtest_report.txt", "w") as f_rep:
        f_rep.write(f"Symbol: {symbol}\n")
        f_rep.write(f"Sharpe: {sharpe:.4f}\n")
        f_rep.write(f"Ann_Return: {ann_ret*100:.2f}%\n")
        f_rep.write(f"MDD: {mdd*100:.2f}%\n")
        f_rep.write(f"Win_Rate: {(returns > 0).mean()*100:.2f}%\n")
    
    print(f"Report saved to tmp/final_backtest_report.txt")

if __name__ == "__main__":
    main()
