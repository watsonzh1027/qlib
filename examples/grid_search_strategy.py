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
    exp_name = "model_showdown"
    recorders_dict = R.list_recorders(experiment_name=exp_name)
    lgbm_rec = None
    
    # Sort by creation time to get the latest
    sorted_recs = sorted(recorders_dict.items(), key=lambda x: x[1].info['start_time'], reverse=True)
    
    for rid, rec in sorted_recs:
        if rec.list_tags().get('model_name') == 'LightGBM':
            lgbm_rec = rec
            break
    
    if not lgbm_rec:
        print(f"LightGBM recorder not found in experiment '{exp_name}'!")
        return

    print(f"Using LightGBM Recorder: {lgbm_rec.info['id']} (started at {lgbm_rec.info['start_time']})")
    
    # Load prediction
    pred = lgbm_rec.load_object("pred.pkl")
    
    # Grid parameters
    # Note: Mean score is around 0.09, so we search around that.
    thresholds = [0.0, 0.08, 0.09, 0.10] 
    stop_losses = [-0.03, -0.05, -0.07, -0.10, None]
    take_profits = [0.05, 0.10, 0.15, 0.20, None]
    
    results = []
    
    # Base configuration
    base_strategy_conf = {
        "class": "CryptoLongShortStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {
            "signal": pred,
            "direction": "long-short",
            "leverage": 1.0,
            "min_sigma_threshold": 0.0, # Disable sigma for now
            "topk": 1,
        }
    }
    
    backtest_conf = {
        "start_time": TEST_START,
        "end_time": TEST_END,
        "exchange_kwargs": {
            "codes": [SYMBOL],
            "freq": FREQ,
            "limit_threshold": None,
            "deal_price": "close",
            "open_cost": 0.0005,
            "close_cost": 0.0005,
            "min_cost": 0.0,
        },
    }
    
    from qlib.backtest import backtest as qlib_backtest
    from qlib.backtest.executor import SimulatorExecutor

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
                    if report_df is None or report_df.empty:
                        continue
                        
                    # Calculate net returns (subtract cost)
                    net_returns = report_df['return'] - report_df.get('cost', 0)
                    
                    ar = net_returns.mean() * 365 * 6 
                    vol = net_returns.std() * np.sqrt(365 * 6)
                    sharpe = ar / vol if vol > 0 else 0
                    
                    cum_wealth = (1 + net_returns).cumprod()
                    cum_ret = cum_wealth.iloc[-1] - 1
                    mdd = (cum_wealth / cum_wealth.cummax() - 1).min()
                    
                    res = {
                        "thr": thr, "sl": sl, "tp": tp,
                        "ann_ret": ar, "sharpe": sharpe, "mdd": mdd, "cum_ret": cum_ret
                    }
                    results.append(res)
                    if count % 10 == 0:
                        print(f"Progress: {count}/{total} done...")
                except Exception as e:
                    pass

    # 4. Summary
    res_df = pd.DataFrame(results)
    if res_df.empty:
        print("No results found!")
        return

    res_df = res_df.sort_values(by="sharpe", ascending=False)
    print("\nGrid Search Results (Top 10 by Sharpe):")
    print(res_df.head(10).to_string(index=False))
    
    os.makedirs("docs", exist_ok=True)
    res_df.to_csv("docs/strategy_grid_search_results.csv", index=False)
    
    best = res_df.iloc[0]
    print(f"\nBest Parameters: thr={best['thr']}, sl={best['sl']}, tp={best['tp']}")
    print(f"Best Sharpe: {best['sharpe']:.4f} | AnnRet: {best['ann_ret']:.2%} | MDD: {best['mdd']:.2%}")

if __name__ == "__main__":
    run_grid_search()
