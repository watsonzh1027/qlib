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

from qlib.utils.logging_config import startlog, endlog

# Configure logging
logger = startlog("train_sample_model")

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Add mapping logic
def map_symbol(symbol):
    """
    Map symbol to qlib format used in the data directory.
    
    Accepts: ETHUSDT, ETH_USDT, ETH/USDT (or any case variation)
    Returns: ethusdt (lowercase, no separator, matching the data directory)
    """
    symbol = symbol.upper()
    # Remove common separators
    symbol = symbol.replace('/', '').replace('_', '').replace('-', '')
    # Return lowercase to match data directory naming (ethusdt, btcusdt, etc.)
    return symbol.lower()

def get_data_dir_for_freq(base_dir, freq):
    """
    Construct the data directory path based on frequency.
    
    If base_dir is 'data/qlib_data/crypto', this will return:
    - 'data/qlib_data/crypto_15min' for freq='15min'
    - 'data/qlib_data/crypto_60min' for freq='60min'
    - 'data/qlib_data/crypto_240min' for freq='240min'
    """
    # Extract the frequency number (e.g., "15" from "15min")
    import re
    match = re.match(r'(\d+)(min|hour|day)', freq)
    if match:
        num, unit = match.groups()
        if unit == 'min':
            return f"{base_dir}_{freq}"
        else:
            # For hour/day, might need different naming
            return f"{base_dir}_{freq}"
    return base_dir

def _compute_ic_icir(pred: pd.Series, label: pd.Series):
    pred = pred.copy()
    label = label.copy()

    if isinstance(pred.index, pd.MultiIndex) and isinstance(label.index, pd.MultiIndex):
        pred_names = pred.index.names
        label_names = label.index.names
        if pred_names != label_names:
            try:
                if all(name in pred_names for name in label_names):
                    pred = pred.reorder_levels(label_names).sort_index()
                if all(name in label_names for name in pred_names):
                    label = label.reorder_levels(pred_names).sort_index()
            except Exception:
                pass

    pred, label = pred.align(label, join="inner")
    df_eval = pd.DataFrame({"pred": pred, "label": label}).dropna()
    if df_eval.empty:
        return float("nan"), float("nan"), 0

    ic = df_eval["pred"].corr(df_eval["label"])
    icir = 0.0

    if isinstance(df_eval.index, pd.MultiIndex):
        level_name = "datetime" if "datetime" in df_eval.index.names else df_eval.index.names[-1]
        level = level_name if level_name else -1
        dates = df_eval.index.get_level_values(level)
        dates = pd.to_datetime(dates, errors="coerce")
        valid_mask = ~dates.isna()
        if valid_mask.any():
            df_eval = df_eval.loc[valid_mask]
            dates = dates[valid_mask]
            daily_groups = df_eval.groupby(dates)
            daily_ic = daily_groups.apply(lambda x: x["pred"].corr(x["label"]) if len(x) > 1 else float("nan"))
            daily_ic = daily_ic.dropna()
            if len(daily_ic) > 1 and daily_ic.std() > 0:
                icir = daily_ic.mean() / daily_ic.std()

    return ic, icir, len(df_eval)

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

    # config_path = Path(args.config)
    # with open(config_path, "r") as f:
    #     config = json.load(f)
    
    from scripts.config_manager import ConfigManager
    cm = ConfigManager(args.config)
    config = cm.config # Access raw config for unsupported sections, but...
    
    # We want resolved values for critical dynamic sections
    # Overwrite raw sections with resolved ones where ConfigManager supports it
    config["data_handler_config"] = cm.get_data_handler_config()
    config["dataset"] = cm.get_dataset_config()
    
    # Get freq from resolved workflow config to ensure consistency
    # Note: ConfigManager resolves <workflow.frequency> to something like "15min"
    raw_freq = cm.get_workflow_config()["frequency"]
    # Fallback to data_collection if workflow freq is missing (unlikely if valid)
    if not raw_freq:
         raw_freq = config.get("data_collection", {}).get("interval", "60min")

    # Init Qlib with frequency-specific data directory
    base_provider_uri = config.get("data", {}).get("bin_data_dir", "data/qlib_data/crypto")
    provider_uri = get_data_dir_for_freq(base_provider_uri, raw_freq)
    qlib.init(provider_uri=provider_uri, region=REG_CN)

    # Prepare Data Handler Config - get instruments
    raw_symbols = config.get("training", {}).get("instruments", [])
    if not raw_symbols:
        dh_cfg = cm.get_data_handler_config()
        if "kwargs" in dh_cfg and "instruments" in dh_cfg["kwargs"]:
            raw_symbols = dh_cfg["kwargs"]["instruments"]
        elif "instruments" in dh_cfg:
            raw_symbols = dh_cfg["instruments"]

    instruments = [map_symbol(s) for s in raw_symbols]

    # Try to load handler config from config
    dh_cfg_from_json = config.get("data_handler_config", {})
    handler_class = dh_cfg_from_json.get("class", "Alpha158")
    module_path = dh_cfg_from_json.get("module_path", "qlib.contrib.data.handler")
    
    # Merge CLI/derived params into JSON-provided kwargs
    final_dh_kwargs = dh_cfg_from_json.get("kwargs", {}).copy()
    
    # Only override with CLI params if they are provided; otherwise use config values
    if args.train_start is not None:
        final_dh_kwargs["start_time"] = args.train_start
    if args.valid_end is not None:
        final_dh_kwargs["end_time"] = args.valid_end
    if args.train_end is not None:
        final_dh_kwargs["fit_end_time"] = args.train_end
    if args.train_start is not None:
        final_dh_kwargs["fit_start_time"] = args.train_start
    
    # Always update instruments and freq
    final_dh_kwargs["instruments"] = instruments
    final_dh_kwargs["freq"] = raw_freq
    
    # Get segments from config or CLI args
    # If CLI args provided, use them; otherwise use config dataset segments
    dataset_config = config.get("dataset", {})
    
    # Build segments - prefer CLI args if provided, else use config
    segments = {}
    if all([args.train_start, args.train_end]):
        segments["train"] = (args.train_start, args.train_end)
    
    if all([args.valid_start, args.valid_end]):
        segments["valid"] = (args.valid_start, args.valid_end)
    
    # If no CLI segments provided, use dataset config segments
    if not segments and "kwargs" in dataset_config and "segments" in dataset_config["kwargs"]:
        config_segments = dataset_config["kwargs"]["segments"]
        # If segments are proportions (integers), they'll be converted later by DatasetH
        # If they're date tuples, use them directly
        segments = config_segments
    
    # Construct Dataset
    final_dataset_config = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": {
                "class": handler_class,
                "module_path": module_path,
                "kwargs": final_dh_kwargs
            },
            "segments": segments
        }
    }
    
    dataset = init_instance_by_config(final_dataset_config)

    # Log segment ranges for train/valid/test
    logger.info(f"Dataset segments: {dataset.segments}")

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

    # Log sample counts per segment (features)
    for seg_name in ["train", "valid", "test"]:
        try:
            seg_df = dataset.prepare(seg_name, col_set="feature")
            seg_count = 0 if seg_df is None else len(seg_df)
            logger.info(f"Segment {seg_name} samples: {seg_count}")
        except Exception as e:
            logger.warning(f"Segment {seg_name} sample count unavailable: {e}")

    # Train
    logger.info("Training model...")
    model.fit(dataset)
    
    # Calculate IC on Validation Set for Tuning
    try:
        # Predict on valid
        pred = model.predict(dataset, segment="valid")
        if isinstance(pred, pd.DataFrame):
            pred = pred.iloc[:, 0]
            
        # Get label
        label = dataset.prepare("valid", col_set="label")
        if isinstance(label, pd.DataFrame):
            label = label.iloc[:, 0]
            
        # Align indices and compute IC/ICIR
        ic, icir, sample_count = _compute_ic_icir(pred, label)
            
        logger.info(f"IC: {ic:.4f} (n={sample_count})")
        logger.info(f"ICIR: {icir:.4f}")
        
    except Exception as e:
        logger.warning(f"Error calculating IC: {e}")
    
    # Predict (on train+valid, maybe? Or just valid? tuning script backtests on TEST)
    # Wait, the tuning script passes --start --end to run_backtest.py matching the TEST fold.
    # So we should probably predict on TEST set? 
    # But this script is 'train_model'. Usually it saves the model. 
    # But saving lightgbm model is easy.
    # Saving dataset is hard.
    
    # We'll save the model object to a pickle file.
    # File name: tmp/tuning/{config_name}_model.pkl
    config_path = Path(args.config)
    model_path = Path("tmp/tuning") / f"{config_path.stem}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
        
    logger.info(f"Model saved to {model_path}")
    endlog(logger, "train_sample_model")

if __name__ == "__main__":
    main()
