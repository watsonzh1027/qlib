import qlib
import pandas as pd
import numpy as np
import torch
import matplotlib.pyplot as plt
from qlib.utils import init_instance_by_config
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, PortAnaRecord, SigAnaRecord
from qlib.contrib.data.loader import Alpha158DL, Alpha360DL
from qlib.log import get_module_logger
import argparse
import os

# ==============================================================================
# PARAMETERS
# ==============================================================================
SYMBOL = "eth_usdt_4h_future"
ALL_SYMBOLS = [
    "eth_usdt_4h_future", "btc_usdt_4h_future", "sol_usdt_4h_future",
    "bnb_usdt_4h_future", "xrp_usdt_4h_future", "aave_usdt_4h_future"
]
FREQ = "240min"
PROVIDER_URI = "data/qlib_data/crypto"

# Time Range
TRAIN_START = "2023-01-01"
TEST_START = "2025-01-01"
# Create buffer for validation
TRAIN_END = (pd.to_datetime(TEST_START) - pd.Timedelta(days=120)).strftime("%Y-%m-%d")
VALID_START = (pd.to_datetime(TRAIN_END) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
VALID_END = (pd.to_datetime(TEST_START) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
START_TIME = TRAIN_START
END_TIME = "2026-01-01" 
TEST_END = "2025-12-31"

# ==============================================================================

def get_common_data_config(use_ts=False):
    f158, n158 = Alpha158DL.get_feature_config()
    f360, n360 = Alpha360DL.get_feature_config()
    
    custom_features = [
        "$high/$low - 1",
        "$close/$vwap - 1",
        "($close-Min($low, 10))/(Max($high, 10)-Min($low, 10)+1e-12)", # RSV 10
        "Sin(2 * 3.1415926 * $weekday / 7)",
        "Cos(2 * 3.1415926 * $weekday / 7)",
        "Sin(2 * 3.1415926 * $hour / 24)",
        "Cos(2 * 3.1415926 * $hour / 24)",
    ]
    custom_names = ["range", "vwap_dev", "rsv10", "weekday_sin", "weekday_cos", "hour_sin", "hour_cos"]

    hybrid_features = f158 + f360 + custom_features
    hybrid_names = [f"A158_{n}" for n in n158] + [f"A360_{n}" for n in n360] + custom_names
    
    # Predict next 12h (3 bars of 4h) return, normalized by vol
    label_cfg = ["(Ref($close, -3)/$close - 1) / (Std(Ref($close, -1)/$close - 1, 20) + 1e-6)"]

    handler_kwargs = {
        "class": "DataHandlerLP",
        "module_path": "qlib.data.dataset.handler",
        "kwargs": {
            "start_time": START_TIME, "end_time": END_TIME,
            "instruments": [SYMBOL],
            "data_loader": {
                "class": "QlibDataLoader",
                "kwargs": {
                    "config": {
                        "feature": (hybrid_features, hybrid_names),
                        "label": (label_cfg, ["LABEL"]),
                    },
                    "freq": FREQ,
                }
            },
            "learn_processors": [
                {"class": "RobustZScoreNorm", "kwargs": {"fields_group": "feature", "clip_outlier": True, "fit_start_time": TRAIN_START, "fit_end_time": TRAIN_END}},
                {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
                {"class": "Fillna", "kwargs": {"fields_group": "label"}},
            ],
        }
    }

    dataset_conf = {
        "class": "TSDatasetH" if use_ts else "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": handler_kwargs,
            "segments": {
                "train": (TRAIN_START, TRAIN_END),
                "valid": (VALID_START, VALID_END),
                "test": (TEST_START, TEST_END),
            },
        },
    }
    if use_ts:
        dataset_conf["kwargs"]["step_len"] = 60
        
    return dataset_conf, len(hybrid_features)

def run_model_showdown():
    logger = get_module_logger("model_showdown")
    qlib.init(provider_uri=PROVIDER_URI, region=qlib.config.REG_CN)

    results = {}

    # Common Strategy and Backtest Config
    strategy_conf = {
        "class": "CryptoLongShortStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {
            "signal": "<PRED>",
            "direction": "long-short",
            "signal_threshold": 0.0,
            "leverage": 1.0,
            "take_profit": None,
            "stop_loss": None,
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
            "min_cost": 0.0,
        },
    }

    # 1. SETUP MODELS
    models = {
        "LightGBM": {
            "model_conf": {
                "class": "LGBModel",
                "module_path": "qlib.contrib.model.gbdt",
                "kwargs": {
                    "objective": "regression",
                    "learning_rate": 0.05,
                    "num_leaves": 128,
                    "max_depth": 5,
                    "subsample": 0.8,
                    "colsample_bytree": 0.8,
                    "lambda_l2": 0.1,
                    "num_threads": 8,
                    "verbosity": -1,
                },
            },
            "use_ts": False
        },
        "ALSTM": {
            "model_conf": {
                "class": "ALSTM",
                "module_path": "qlib.contrib.model.pytorch_alstm_ts",
                "kwargs": {
                    "loss": "huber",
                    "hidden_size": 256,
                    "num_layers": 2,
                    "dropout": 0.5,
                    "n_epochs": 50,
                    "lr": 2e-4,
                    "early_stop": 15,
                    "batch_size": 1024,
                    "GPU": 0 if torch.cuda.is_available() else -1,
                },
            },
            "use_ts": True
        }
    }

    for name, m_info in models.items():
        logger.info(f"--- Processing Model: {name} ---")
        dataset_conf, d_feat = get_common_data_config(use_ts=m_info["use_ts"])
        
        if name == "ALSTM":
            m_info["model_conf"]["kwargs"]["d_feat"] = d_feat

        with R.start(experiment_name="model_showdown_v1"):
            R.set_tags(model_name=name)
            
            model = init_instance_by_config(m_info["model_conf"])
            dataset = init_instance_by_config(dataset_conf)
            
            # Training
            model.fit(dataset)

            # Feature Importance for LightGBM
            if name == "LightGBM":
                try:
                    import pandas as pd
                    importance = model.model.feature_importance(importance_type='gain')
                    feat_importance = pd.DataFrame({'feature': hybrid_names, 'importance': importance})
                    feat_importance = feat_importance.sort_values(by='importance', ascending=False).reset_index(drop=True)
                    logger.info("Top 20 Features for LightGBM (by Gain):")
                    logger.info(f"\n{feat_importance.head(20).to_string()}")
                    feat_importance.to_csv("docs/lgbm_feature_importance.csv", index=False)
                except Exception as e:
                    logger.error(f"Failed to extract Feature Importance: {e}")
            
            # Signal Analysis
            sig_record = SignalRecord(model=model, dataset=dataset, recorder=R.get_recorder())
            sig_record.generate()
            
            sar = SigAnaRecord(recorder=R.get_recorder())
            sar.generate()
            
            # Filter pred for SYMBOL only and maintain MultiIndex for Backtest
            pred_all = R.get_recorder().load_object("pred.pkl")
            pred = pred_all.loc[pred_all.index.get_level_values("instrument") == SYMBOL]
            R.get_recorder().save_objects(**{"pred.pkl": pred})

            # Backtest (Strictly on SYMBOL)
            logger.info(f"Running backtest for {SYMBOL}...")
            par = PortAnaRecord(
                recorder=R.get_recorder(), 
                config={
                    "strategy": strategy_conf,
                    "executor": {"class": "SimulatorExecutor", "module_path": "qlib.backtest.executor", "kwargs": {"time_per_step": FREQ, "generate_portfolio_metrics": True}},
                    "backtest": backtest_conf,
                }
            )
            par.generate()
            
            # Manual IC Calculation (Strictly on SYMBOL)
            # Fetch label for the filtered pred index
            label = dataset.handler.fetch(pred.index, col_set="label")
            if isinstance(label, pd.DataFrame):
                label = label.iloc[:, 0]
            
            combined = pd.concat([pred, label], axis=1).dropna()
            ic = combined.corr().iloc[0, 1] if len(combined) > 0 else 0
            rank_ic = combined.corr(method="spearman").iloc[0, 1] if len(combined) > 0 else 0
            
            # Collect results for summary
            metrics = R.get_recorder().list_metrics()
            # Extract main metrics
            freq_key = "240min"
            ann_ret = metrics.get(f"{freq_key}.excess_return_with_cost.annualized_return", 0)
            sharpe = metrics.get(f"{freq_key}.excess_return_with_cost.information_ratio", 0)
            mdd = metrics.get(f"{freq_key}.excess_return_with_cost.max_drawdown", 0)
            
            results[name] = {
                "IC": ic,
                "RankIC": rank_ic,
                "Ann_Return": ann_ret,
                "Sharpe": sharpe,
                "Max_Drawdown": mdd
            }

    # 2. FINAL REPORT
    print("\n" + "="*70)
    print(f"{'Model Name':<15} | {'IC':<8} | {'RankIC':<8} | {'Ann Ret':<10} | {'Sharpe':<8} | {'MDD':<10}")
    print("-" * 70)
    for name, res in results.items():
        print(f"{name:<15} | {res['IC']:<8.4f} | {res['RankIC']:<8.4f} | {res['Ann_Return']:<10.2%} | {res['Sharpe']:<8.4f} | {res['Max_Drawdown']:<10.2%}")
    print("="*70 + "\n")

    plt.figure(figsize=(10, 6))
    recorders = R.list_recorders(experiment_name="model_showdown_v1")
    for name in results:
        # Find the one with tag model_name == name
        for rid, rec in recorders.items():
            if rec.list_tags().get("model_name") == name:
                report = rec.load_object("portfolio_analysis/report_normal_240min.pkl")
                if report is not None:
                    cum_ret = (report["return"] - report["cost"]).cumsum()
                    plt.plot(cum_ret, label=f"{name} (Excess)")
                break

    plt.title("Model Showdown: LightGBM vs ALSTM (ETH 4H)")
    plt.xlabel("Datetime")
    plt.ylabel("Cumulative Excess Return")
    plt.legend()
    plt.grid(True)
    plt.savefig("docs/model_showdown_comparison.png")
    logger.info("Showdown comparison plot saved to docs/model_showdown_comparison.png")

if __name__ == "__main__":
    run_model_showdown()
