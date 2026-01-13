import qlib
import pandas as pd
import numpy as np
import torch
from qlib.utils import init_instance_by_config
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, PortAnaRecord, SigAnaRecord
from qlib.contrib.data.loader import Alpha158DL, Alpha360DL
from qlib.log import get_module_logger
import argparse
import os

# ==============================================================================
# 1. PARAMETERS
# ==============================================================================
parser = argparse.ArgumentParser()
parser.add_argument("--symbol", type=str, default="eth_usdt_4h_future")
parser.add_argument("--freq", type=str, default="240min")
parser.add_argument("--train_start", type=str, default="2023-01-01")
parser.add_argument("--test_start", type=str, default="2025-01-01")
parser.add_argument("--leverage", type=float, default=2.0)
parser.add_argument("--threshold", type=float, default=0.005)
args = parser.parse_args()

PROVIDER_URI = "data/qlib_data/crypto"
SYMBOL = args.symbol
FREQ = args.freq

# Time Range
TRAIN_START = args.train_start
TEST_START = args.test_start
TRAIN_END = (pd.to_datetime(TEST_START) - pd.Timedelta(days=180)).strftime("%Y-%m-%d")
VALID_START = (pd.to_datetime(TRAIN_END) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
VALID_END = (pd.to_datetime(TEST_START) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
START_TIME = TRAIN_START
END_TIME = "2026-01-01" 
TEST_END = "2025-12-31"

# ==============================================================================

def run_crypto_backtest():
    import logging
    logging.getLogger("CryptoLongShortStrategy").setLevel(logging.DEBUG)
    logger = get_module_logger("crypto_backtest")
    logger.setLevel(logging.DEBUG)
    qlib.init(provider_uri=PROVIDER_URI, region=qlib.config.REG_CN)
    logger.info(f"Initialized Qlib for {SYMBOL} backtest")

    # 1. Data Handler Config (Hybrid Alpha158 + Alpha360)
    f158, n158 = Alpha158DL.get_feature_config()
    f360, n360 = Alpha360DL.get_feature_config()
    hybrid_features = f158 + f360
    hybrid_names = [f"A158_{n}" for n in n158] + [f"A360_{n}" for n in n360]
    
    # Volatility Scaled Label
    label_cfg = ["(Ref($close, -1)/$close - 1) / (Std(Ref($close, -1)/$close - 1, 20) + 1e-6)"]

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

    # 2. Dataset Config
    dataset_conf = {
        "class": "TSDatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": handler_kwargs,
            "segments": {
                "train": (TRAIN_START, TRAIN_END),
                "valid": (VALID_START, VALID_END),
                "test": (TEST_START, TEST_END),
            },
            "step_len": 30,
        },
    }

    # 3. Model Config (ALSTM)
    model_conf = {
        "class": "ALSTM",
        "module_path": "qlib.contrib.model.pytorch_alstm_ts",
        "kwargs": {
            "d_feat": len(hybrid_features),
            "hidden_size": 128,
            "num_layers": 2,
            "dropout": 0.1,
            "n_epochs": 50,
            "lr": 1e-3,
            "early_stop": 15,
            "batch_size": 1024,
            "GPU": 0 if torch.cuda.is_available() else -1,
        },
    }

    # 4. Strategy Config (Our New CryptoLongShortStrategy)
    strategy_conf = {
        "class": "CryptoLongShortStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {
            "signal": "<PRED>",
            "direction": "long-short",
            "signal_threshold": args.threshold,
            "leverage": args.leverage,
            "take_profit": 0.08,
            "stop_loss": -0.04,
            "max_drawdown_limit": 0.20,
            "topk": 1,
        }
    }

    # 5. Backtest/Executor Config
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
            "open_cost": 0.0005, # OKX taker fee approx
            "close_cost": 0.0005,
            "min_cost": 0.0,
        },
    }
    
    executor_conf = {
        "class": "SimulatorExecutor",
        "module_path": "qlib.backtest.executor",
        "kwargs": {
            "time_per_step": FREQ,
            "generate_portfolio_metrics": True,
        },
    }

    # 6. Run Workflow
    with R.start(experiment_name="crypto_final_backtest"):
        # Training
        model = init_instance_by_config(model_conf)
        dataset = init_instance_by_config(dataset_conf)
        model.fit(dataset)
        
        # Signal Generation/Analysis
        sig_record = SignalRecord(model=model, dataset=dataset, recorder=R.get_recorder())
        sig_record.generate()
        
        sar = SigAnaRecord(recorder=R.get_recorder())
        sar.generate()
        
        # Portfolio Backtest
        par = PortAnaRecord(
            recorder=R.get_recorder(), 
            config={
                "strategy": strategy_conf,
                "executor": executor_conf,
                "backtest": backtest_conf,
            }
        )
        par.generate()
        
        logger.info("Backtest finished. Results stored in mlruns.")

if __name__ == "__main__":
    run_crypto_backtest()
