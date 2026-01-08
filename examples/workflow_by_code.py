#  Copyright (c) Microsoft Corporation.
#  Licensed under the MIT License.
"""
Qlib provides two kinds of interfaces.
(1) Users could define the Quant research workflow by a simple configuration.
(2) Qlib is designed in a modularized way and supports creating research workflow by code just like building blocks.

The interface of (1) is `qrun XXX.yaml`.  The interface of (2) is script like this, which nearly does the same thing as `qrun XXX.yaml`
"""
import sys
from pathlib import Path
import os
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import qlib
from qlib.utils import init_instance_by_config, flatten_dict
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, PortAnaRecord, SigAnaRecord
from scripts.data_collector.crypto.collector import Run as CryptoRun
from scripts.dump_bin import DumpDataAll

if __name__ == "__main__":
    # 1. Collect and Normalize Crypto Data
    # Use the configuration from config/workflow.json
    config_path = "config/workflow.json"
    crypto_run = CryptoRun(config_path=config_path)
    
    print("Step 1: Downloading and Normalizing Crypto Data...")
    crypto_run.download_data()
    crypto_run.normalize_data()

    # 2. Convert CSV to Qlib Binary Format
    # These paths are based on typical workflow.json settings
    csv_path = "data/klines"
    qlib_data_path = "data/qlib_data/crypto"
    
    print(f"Step 2: Dumping Data from {csv_path} to {qlib_data_path}...")
    DumpDataAll(
        data_path=csv_path,
        qlib_dir=qlib_data_path,
        freq="60min",
        date_field_name="date",
        symbol_field_name="symbol",
        include_fields="open,high,low,close,volume,vwap"
    ).dump()

    # 3. Initialize Qlib
    print("Step 3: Initializing Qlib...")
    qlib.init(provider_uri=qlib_data_path)

    # 4. Define Task Configuration
    # We use Alpha158 as the feature handler and LightGBM as the model
    market = "all" # Refers to all instruments in the binary data
    benchmark = None # No benchmark for crypto usually
    
    task_config = {
        "model": {
            "class": "LGBModel",
            "module_path": "qlib.contrib.model.gbdt",
            "kwargs": {
                "loss": "mse",
                "colsample_bytree": 0.8879,
                "learning_rate": 0.1,
                "subsample": 0.8789,
                "lambda_l1": 205.6999,
                "lambda_l2": 580.9768,
                "max_depth": 8,
                "num_leaves": 210,
                "num_threads": 20,
                "num_boost_round": 100,
            },
        },
        "dataset": {
            "class": "DatasetH",
            "module_path": "qlib.data.dataset",
            "kwargs": {
                "handler": {
                    "class": "Alpha158",
                    "module_path": "qlib.contrib.data.handler",
                    "kwargs": {
                        "start_time": "2025-01-01",
                        "end_time": "2025-10-31",
                        "fit_start_time": "2025-01-01",
                        "fit_end_time": "2025-06-01",
                        "instruments": market,
                        "freq": "60min",
                    },
                },
                "segments": {
                    "train": ("2025-01-01", "2025-06-01"),
                    "valid": ("2025-06-02", "2025-08-01"),
                    "test": ("2025-08-02", "2025-10-31"),
                },
            },
        },
    }

    port_analysis_config = {
        "executor": {
            "class": "SimulatorExecutor",
            "module_path": "qlib.backtest.executor",
            "kwargs": {
                "time_per_step": "60min",
                "generate_portfolio_metrics": True,
            },
        },
        "strategy": {
            "class": "TopkDropoutStrategy",
            "module_path": "qlib.contrib.strategy.signal_strategy",
            "kwargs": {
                "signal": None, # Will be set during backtest
                "topk": 5,
                "n_drop": 1,
            },
        },
        "backtest": {
            "start_time": "2025-08-02",
            "end_time": "2025-10-31",
            "account": 1000000,
            "benchmark": benchmark,
            "exchange_kwargs": {
                "freq": "60min",
                "limit_threshold": None,
                "deal_price": "close",
                "open_cost": 0.001,
                "close_cost": 0.001,
                "min_cost": 0.001,
            },
        },
    }

    # 5. Execute Workflow
    model = init_instance_by_config(task_config["model"])
    dataset = init_instance_by_config(task_config["dataset"])

    # Start experiment
    with R.start(experiment_name="crypto_workflow"):
        print("Step 4: Training Model...")
        R.log_params(**flatten_dict(task_config))
        model.fit(dataset)
        R.save_objects(**{"params.pkl": model})

        # Predict
        print("Step 5: Generating Predictions...")
        recorder = R.get_recorder()
        sr = SignalRecord(model, dataset, recorder)
        sr.generate()

        # Signal Analysis
        print("Step 6: Analyzing Signals...")
        sar = SigAnaRecord(recorder)
        sar.generate()

        # Backtest
        print("Step 7: Running Backtest...")
        # Update strategy with model and dataset
        port_analysis_config["strategy"]["kwargs"]["signal"] = (model, dataset)
        par = PortAnaRecord(recorder, port_analysis_config, "60min")
        par.generate()

    print("Workflow completed successfully!")
