import argparse
import numpy as np
import pandas as pd
from loguru import logger
import matplotlib.pyplot as plt
import os

import qlib
from qlib.constant import REG_CN
from qlib.utils import init_instance_by_config
from qlib.data.dataset import DatasetH

# ==============================================================================
# Configuration
# ==============================================================================
parser = argparse.ArgumentParser()
parser.add_argument("--symbol", type=str, default="ETH_USDT_4H_FUTURE")
parser.add_argument("--freq", type=str, default="240min")
parser.add_argument("--train_start", type=str, default="2023-01-01")
parser.add_argument("--test_start", type=str, default="2025-01-01")
args = parser.parse_args()

PROVIDER_URI = "data/qlib_data/crypto"
SYMBOL = args.symbol
FREQ = args.freq

# Model settings
MODEL_CLASS = "LGBModel"
MODEL_MODULE = "qlib.contrib.model.gbdt"

# Time Range
TRAIN_START = args.train_start
TEST_START = args.test_start
TRAIN_END = (pd.to_datetime(TEST_START) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
START_TIME = TRAIN_START
END_TIME = "2026-01-01" 

# ==============================================================================

def run_importance_analysis():
    qlib.init(provider_uri=PROVIDER_URI, region=REG_CN)
    logger.info(f"Running Feature Importance Analysis for {SYMBOL} ({FREQ})")

    # 1. Feature Engineering with VWAP focus
    features = [
        # Basic Price Returns
        "($close-Ref($close,1))/Ref($close,1)",
        # VWAP specific features
        "($vwap-$close)/$close",                # Distance between VWAP and Close
        "($vwap-Ref($vwap,1))/Ref($vwap,1)",    # VWAP Return
        "Std($vwap, 20)/$vwap",                 # VWAP Volatility
        "Mean($vwap, 5)/$vwap - 1",             # VWAP Moving Average Convergence
        # Other Tech
        "Std($close, 20)/$close",
        "($close-Min($close, 20))/(Max($close, 20)-Min($close, 20)+1e-6)",
        "Mean($volume, 5)/($volume+1e-6)",      # Volume Change
    ]
    
    feature_names = [
        "Return_1",
        "VWAP_Close_Diff",
        "VWAP_Return_1",
        "VWAP_Vol_20",
        "VWAP_MA_5_Diff",
        "Close_Vol_20",
        "Price_Range_20",
        "Vol_Change_5"
    ]
    
    # Label
    label = ["Ref($close, -1)/$close - 1"]

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
                        "feature": (features, feature_names),
                        "label": (label, ["LABEL"]),
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

    # 2. Dataset
    dataset_conf = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": handler_kwargs,
            "segments": {
                "train": (TRAIN_START, TRAIN_END),
                "test": (TEST_START, "2025-12-31"),
            },
        },
    }
    dataset = init_instance_by_config(dataset_conf)

    # 3. Model Training
    params = {
        "loss": "mse",
        "learning_rate": 0.05,
        "max_depth": 5,
        "num_leaves": 31,
        "verbosity": -1,
        "num_boost_round": 100,
    }
    model = init_instance_by_config({"class": MODEL_CLASS, "module_path": MODEL_MODULE, "kwargs": params})
    model.fit(dataset)
    
    # 4. Feature Importance
    # qlib.contrib.model.gbdt.LGBModel wraps lightgbm
    lpb_model = model.model
    importance_gain = lpb_model.feature_importance(importance_type='gain')
    importance_split = lpb_model.feature_importance(importance_type='split')
    
    df_importance = pd.DataFrame({
        'Feature': feature_names,
        'Gain': importance_gain,
        'Split': importance_split
    }).sort_values(by='Gain', ascending=False)
    
    print("\n" + "="*50)
    print(f"FEATURE IMPORTANCE REPORT ({SYMBOL})")
    print("="*50)
    print(df_importance.to_string(index=False))
    print("="*50)
    
    # Save a plot
    plt.figure(figsize=(10, 6))
    plt.barh(df_importance['Feature'], df_importance['Gain'])
    plt.xlabel('Importance (Gain)')
    plt.title(f'LightGBM Feature Importance (Gain) - {SYMBOL}')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig('docs/feature_importance.png')
    logger.info("Saved importance plot to docs/feature_importance.png")

if __name__ == "__main__":
    run_importance_analysis()
