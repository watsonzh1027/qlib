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
from qlib.data.dataset.handler import DataHandlerLP
from qlib.contrib.model.gbdt import LGBModel
from qlib.utils.logging_config import setup_logging

# Configure logging
logger = setup_logging()

# Add mapping logic
def map_symbol(symbol):
    symbol = symbol.upper()
    if "_" not in symbol:
        # Assume format like BTCUSDT -> BTC_USDT_4H_FUTURE
        if symbol.endswith("USDT"):
            coin = symbol[:-4]
            return f"{coin}_USDT_4H_FUTURE"
    return symbol

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--model", default="lightgbm")
    parser.add_argument("--train-start")
    parser.add_argument("--train-end")
    parser.add_argument("--valid-start")
    parser.add_argument("--valid-end")
    parser.add_argument("--embedding", action="store_true") # Ignored for now
    args, unknown = parser.parse_known_args()

    config_path = Path(args.config)
    with open(config_path, "r") as f:
        config = json.load(f)

    # Init Qlib
    provider_uri = config.get("data", {}).get("bin_data_dir", "data/qlib_data/crypto")
    qlib.init(provider_uri=provider_uri, region=REG_CN)

    # Prepare Data Handler Config
    # We need to construct a standard Qlib DataHandler config
    # The symbol is in config["training"]["instruments"] (list)
    raw_symbols = config.get("training", {}).get("instruments", [])
    instruments = [map_symbol(s) for s in raw_symbols]
    
    # Check if instruments exist
    # If not, maybe use 'crypto_4h' or similar
    
    dh_config = {
        "start_time": args.train_start,
        "end_time": args.valid_end,
        "fit_start_time": args.train_start,
        "fit_end_time": args.train_end,
        "instruments": instruments,
        "infer_processors": [],
        "learn_processors": [],
        "freq": "240min"  # Force 4h
    }
    
    # Try to load handler config from config
    dh_cfg_from_json = config.get("data_handler_config", {})
    handler_class = dh_cfg_from_json.get("class", "Alpha158")
    module_path = dh_cfg_from_json.get("module_path", "qlib.contrib.data.handler")
    
    # Construct Dataset
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
                "train": (args.train_start, args.train_end),
                "valid": (args.valid_start, args.valid_end),
            }
        }
    }
    
    dataset = init_instance_by_config(dataset_config)

    # Initialize Model
    # Extract params from config
    model_params = config.get("training", {}).get("models", {}).get(args.model, {})
    
    # Default model config (LGBModel)
    if args.model == "lightgbm":
        model_config = {
            "class": "LGBModel",
            "module_path": "qlib.contrib.model.gbdt",
            "kwargs": {
                "loss": "mse",
                "colsample_bytree": 0.8,
                "learning_rate": model_params.get("learning_rate", 0.05),
                "subsample": 0.8,
                "lambda_l2": model_params.get("lambda_l2", 0.1),
                "max_depth": int(model_params.get("max_depth", 5)),
                "num_leaves": int(model_params.get("num_leaves", 15)),
                "num_threads": int(model_params.get("num_threads", 4)),
                "num_boost_round": 200,
                "early_stopping_rounds": 50
            }
        }
    else:
        # Fallback or support other models
        raise ValueError(f"Model {args.model} not supported in this script yet")

    model = init_instance_by_config(model_config)

    # Train
    print("Training model...")
    model.fit(dataset)
    
    # Predict (on train+valid, maybe? Or just valid? tuning script backtests on TEST)
    # Wait, the tuning script passes --start --end to run_backtest.py matching the TEST fold.
    # So we should probably predict on TEST set? 
    # But this script is 'train_model'. Usually it saves the model. 
    # But saving lightgbm model is easy.
    # Saving dataset is hard.
    
    # We'll save the model object to a pickle file.
    # File name: tmp/tuning/{config_name}_model.pkl
    model_path = Path("tmp/tuning") / f"{config_path.stem}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
        
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    main()
