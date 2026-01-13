import qlib
import pandas as pd
import numpy as np
from qlib.workflow import R
from qlib.contrib.report import analysis_model, analysis_position
from qlib.utils import init_instance_by_config
from qlib.workflow.record_temp import PortAnaRecord
import logging
import os

# Setup paths and symbols
PROVIDER_URI = "data/qlib_data/crypto"
SYMBOL = "eth_usdt_4h_future"
FREQ = "240min"
TEST_START = "2024-01-01"
TEST_END = "2025-12-31"

qlib.init(provider_uri=PROVIDER_URI, region=qlib.config.REG_CN)

# Disable most logging to speed up and clean output
logging.getLogger("qlib").setLevel(logging.ERROR)

def run_grid_search():
    # 1. Find the LightGBM recorder
    exp_name = "model_showdown_v1"
    recoders_dict = R.list_recorders(experiment_name=exp_name)
    lgbm_rec = None
    for rid in recoders_dict:
        rec = R.get_recorder(recorder_id=rid, experiment_name=exp_name)
        if rec.list_tags().get('model_name') == 'LightGBM':
            lgbm_rec = rec
            break
    
    if not lgbm_rec:
        print("LightGBM recorder not found!")
        return

    print(f"Found LightGBM Recorder: {lgbm_rec.info['id']}")
    
    # Load filtered prediction for ETH only (already filtered in model_showdown.py)
    # Actually, model_showdown.py filtered it and saved it.
    pred = lgbm_rec.load_object("pred.pkl")
    
    # Grid parameters
    thresholds = [0.0, 0.005, 0.01]
    stop_losses = [-0.03, -0.05, -0.07]
    take_profits = [0.05, 0.10, 0.15]
    
    results = []
    
    # Base configuration
    base_strategy_conf = {
        "class": "CryptoLongShortStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {
            "signal": pred, # Pass the pred dataframe directly
            "direction": "long-short",
            "leverage": 1.0,
            "max_drawdown_limit": 1.0,
            "topk": 1,
        }
    }
    
    backtest_conf = {
        "start_time": TEST_START,
        "end_time": TEST_END,
        "account": 1000000,
        "benchmark": None,
        "exchange_kwargs": {
            "codes": [SYMBOL],
            "freq": FREQ,
            "limit_threshold": None,
            "deal_price": "close",
            "open_cost": 0.0005,
            "close_cost": 0.0005,
            "min_cost": 5,
        },
    }

    count = 0
    total = len(thresholds) * len(stop_losses) * len(take_profits)
    
    print(f"Starting Grid Search (Total {total} combinations)...")
    
    for thr in thresholds:
        for sl in stop_losses:
            for tp in take_profits:
                count += 1
                strategy_conf = base_strategy_conf.copy()
                strategy_conf["kwargs"] = base_strategy_conf["kwargs"].copy()
                strategy_conf["kwargs"].update({
                    "signal_threshold": thr,
                    "stop_loss": sl,
                    "take_profit": tp
                })
                
                # We need to run the backtest. 
                # Since we don't want to create 27 recorders in the main experiment, 
                # we will use a dedicated temporary experiment or just run the simulation.
                
                from qlib.backtest import backtest as qlib_backtest
                from qlib.backtest.executor import SimulatorExecutor
                
                executor = SimulatorExecutor(time_per_step=FREQ, generate_portfolio_metrics=True)
                
                try:
                    portfolio_metric_dict, indicator_dict = qlib_backtest(
                        start_time=TEST_START,
                        end_time=TEST_END,
                        strategy=strategy_conf,
                        executor=executor,
                        benchmark=None,
                        exchange_kwargs=backtest_conf["exchange_kwargs"],
                    )
                    
                    report_df, _ = portfolio_metric_dict.get(FREQ)
                    
                    # Calculate metrics
                    # Excess return with cost is usually what we care about
                    # In this case, since benchmark is None, excess return = absolute return
                    
                    ar = report_df['return'].mean() * 365 * (24*60 / 240) # Annualized return approx
                    vol = report_df['return'].std() * np.sqrt(365 * (24*60 / 240))
                    sharpe = ar / vol if vol > 0 else 0
                    
                    cum_ret = (1 + report_df['return']).prod() - 1
                    mdd = (report_df['return'].cumsum() - report_df['return'].cumsum().cummax()).min()
                    # More accurate MDD:
                    cum_wealth = (1 + report_df['return']).cumprod()
                    mdd = (cum_wealth / cum_wealth.cummax() - 1).min()
                    
                    res = {
                        "thr": thr, "sl": sl, "tp": tp,
                        "ann_ret": ar, "sharpe": sharpe, "mdd": mdd, "cum_ret": cum_ret
                    }
                    results.append(res)
                    print(f"[{count}/{total}] thr={thr}, sl={sl}, tp={tp} | Sharpe: {sharpe:.4f}, AnnRet: {ar:.2%}, MDD: {mdd:.2%}")
                except Exception as e:
                    print(f"[{count}/{total}] Error for thr={thr}, sl={sl}, tp={tp}: {e}")

    # 4. Summary
    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values(by="sharpe", ascending=False)
    print("\nGrid Search Results (Top 10 by Sharpe):")
    print(res_df.head(10).to_string(index=False))
    
    res_df.to_csv("docs/strategy_grid_search_results.csv", index=False)
    
    best = res_df.iloc[0]
    print(f"\nBest Parameters: thr={best['thr']}, sl={best['sl']}, tp={best['tp']}")
    print(f"Best Sharpe: {best['sharpe']:.4f}")

if __name__ == "__main__":
    run_grid_search()
