import qlib
import pandas as pd
import numpy as np
import optuna
import matplotlib.pyplot as plt
from qlib.utils import init_instance_by_config
from qlib.data import D
from qlib.utils.logging_config import get_logger, setup_logging
from qlib.contrib.data.loader import Alpha158DL, Alpha360DL
from pathlib import Path
import os
import torch
from scipy.stats import pearsonr, spearmanr
import threading
import time as t_module

# ==============================================================================
# 1. PARAMETERS - ADJUST THESE AS NEEDED
# ==============================================================================
PROVIDER_URI = "data/qlib_data/crypto"
SYMBOL = "eth_usdt_4h_future"  # ETH_USDT 4H
FREQ = "240min"

# Data Configuration
DATA_HANDLER_CLASS = "DataHandlerLP" # Use base class for hybrid features
DATA_HANDLER_MODULE = "qlib.data.dataset.handler"
TS_STEP_LEN = 20 # Sequence length for LSTM
CORR_THRESHOLD = 0.98 # Threshold to remove highly correlated features

# Model Configuration
MODEL_CLASS = "ALSTM"
MODEL_MODULE = "qlib.contrib.model.pytorch_alstm_ts"

# Time Range
START_TIME = "2020-01-01"
END_TIME = "2026-01-01" 
TRAIN_START = "2020-01-01"
TRAIN_END = "2023-12-31"
VALID_START = "2024-01-01"
VALID_END = "2024-12-31"
TEST_START = "2025-01-01"
TEST_END = "2025-12-31"

# Optimization Configuration
N_TRIALS = 20  
GPU_ID = 0 if torch.cuda.is_available() else -1

# Visualization Settings
PLOT_RANGE = 200

# ==============================================================================

def inspect_data(logger, df, name="Dataset"):
    """
    Inspects the dataset for anomalies and potential issues.
    """
    if not hasattr(df, "isna"):
        logger.info(f"--- {name} is {type(df)}. Skipping detailed inspection. ---")
        return
    logger.info(f"--- Inspecting {name} ---")
    total_samples = len(df)
    logger.info(f"Total samples: {total_samples}")
    
    # Check for NaN and Inf
    nan_count = df.isna().sum().sum()
    inf_count = np.isinf(df.values).sum()
    
    if nan_count > 0:
        logger.warning(f"Found {nan_count} NaN values in {name}.")
    else:
        logger.info(f"No NaN values found in {name}.")
        
    if inf_count > 0:
        logger.warning(f"Found {inf_count} Inf values in {name}.")
    else:
        logger.info(f"No Inf values found in {name}.")
        
    # Stats on features
    logger.info(f"Min value across all features: {df.min().min():.4f}")
    logger.info(f"Max value across all features: {df.max().max():.4f}")
    
    extreme_range = 10.0 # Threshold for 'extreme' in standardized data
    extreme_count = (np.abs(df.values) > extreme_range).sum()
    if extreme_count > 0:
        logger.warning(f"Found {extreme_count} values outside [-{extreme_range}, {extreme_range}] range.")
    
    return {
        "nan_count": nan_count,
        "inf_count": inf_count,
        "total_samples": total_samples
    }

def drop_correlated_features(df, threshold=0.98, logger=None):
    """
    Identifies and drops highly correlated features and constant features.
    """
    if logger:
        logger.info(f"Checking for redundant features with threshold {threshold}...")
    
    # 1. Drop constant features
    constant_cols = [c for c in df.columns if df[c].nunique() <= 1]
    if logger and len(constant_cols) > 0:
        logger.info(f"Dropped {len(constant_cols)} constant features: {constant_cols}")
    df = df.drop(columns=constant_cols)

    # 2. Drop highly correlated features
    corr_matrix = df.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    to_drop = [column for column in upper.columns if any(upper[column] > threshold)]
    
    if logger:
        logger.info(f"Dropped {len(to_drop)} features due to high correlation ({len(df.columns) - len(to_drop)} remaining).")
        if len(to_drop) > 0:
            logger.debug(f"Dropped features: {to_drop}")
            
    return df.drop(columns=to_drop), constant_cols + to_drop

def run_model_test():
    # 0. Prepare Hybrid Features
    f158, n158 = Alpha158DL.get_feature_config()
    f360, n360 = Alpha360DL.get_feature_config()
    
    # Combined features and unique names
    hybrid_features = f158 + f360
    hybrid_names = [f"A158_{n}" for n in n158] + [f"A360_{n}" for n in n360]

    # 1. Initialize Qlib
    import logging as logging_module
    qlib.init(provider_uri=PROVIDER_URI, logging_level=logging_module.WARNING)
    
    # 2. Setup Logging
    setup_logging()
    logger = get_logger("model_test")
    logger.info(f"Step 1: Qlib initialized. Hybrid Features: {len(hybrid_features)}")
    market = [SYMBOL]

    # 3. Data Preparation
    handler_kwargs = {
        "class": DATA_HANDLER_CLASS,
        "module_path": DATA_HANDLER_MODULE,
        "kwargs": {
            "start_time": START_TIME,
            "end_time": END_TIME,
            "instruments": market,
            "data_loader": {
                "class": "QlibDataLoader",
                "kwargs": {
                    "config": {
                        "feature": (hybrid_features, hybrid_names),
                        "label": (["Ref($close, -2)/Ref($close, -1) - 1"], ["LABEL0"]),
                    },
                    "freq": FREQ,
                }
            },
            "infer_processors": [
                {"class": "ProcessInf", "kwargs": {}},
                {"class": "Fillna", "kwargs": {}},
            ],
            "learn_processors": [
                {"class": "DropnaProcessor", "kwargs": {"fields_group": "feature"}},
                {
                    "class": "RobustZScoreNorm", 
                    "kwargs": {
                        "fields_group": "feature", 
                        "clip_outlier": True,
                        "fit_start_time": TRAIN_START,
                        "fit_end_time": TRAIN_END,
                    }
                },
            ],
        },
    }

    dataset_config = {
        "class": "DatasetH", # Use simple DatasetH initially for correlation
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

    # Heartbeat thread to show activity during long initialization and prepare() calls
    stop_heartbeat = False
    def heartbeat():
        start_t = t_module.time()
        while not stop_heartbeat:
            t_module.sleep(60)
            elapsed = (t_module.time() - start_t) / 60
            logger.info(f"Still processing data... (Elapsed: {elapsed:.1f} minutes)")
    
    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    try:
        logger.info(f"Loading Initial Dataset for Feature Selection...")
        dataset_init = init_instance_by_config(dataset_config)
        
        # Data Inspection & Feature Selection
        logger.info("Preparing training features for correlation analysis...")
        df_train_init = dataset_init.prepare("train", col_set="feature")
        
        # Feature Selection: Remove correlated features
        df_train_filtered, to_drop = drop_correlated_features(df_train_init, threshold=CORR_THRESHOLD, logger=logger)
        
        # Identify indices to keep
        remaining_indices = [i for i, name in enumerate(hybrid_names) if name not in to_drop]
        final_features = [hybrid_features[i] for i in remaining_indices]
        final_names = [hybrid_names[i] for i in remaining_indices]
        
        # Re-initialize the final handler and dataset with reduced features and TSDatasetH
        logger.info(f"Re-initializing TSDatasetH with {len(final_names)} selected features...")
        handler_kwargs["kwargs"]["data_loader"]["kwargs"]["config"]["feature"] = (final_features, final_names)
        dataset_config["class"] = "TSDatasetH"
        dataset_config["kwargs"]["handler"] = handler_kwargs
        dataset_config["kwargs"]["step_len"] = TS_STEP_LEN
        dataset = init_instance_by_config(dataset_config)
        
        logger.info("Preparing final datasets...")
        df_train_feat = dataset.prepare("train", col_set="feature")
        df_train_label = dataset.prepare("train", col_set="label")
    finally:
        stop_heartbeat = True
    
    inspect_data(logger, df_train_filtered, name="Training Features (Selected)")
    inspect_data(logger, df_train_label, name="Training Labels")

    actual_d_feat = len(df_train_filtered.columns)
    logger.info(f"Dataset loaded. Final feature dimension after selection: {actual_d_feat}")

    alstm_d_feat = actual_d_feat

    # 4. Hyperparameter Optimization with Optuna
    logger.info(f"Step 2: Optimizing {MODEL_CLASS} with Optuna ({N_TRIALS} trials)")
    
    def objective(trial):
        # We need to use the dataset with SELECTED features
        params = {
            "d_feat": alstm_d_feat,
            "hidden_size": trial.suggest_categorical("hidden_size", [16, 32, 64]),
            "num_layers": trial.suggest_int("num_layers", 1, 3),
            "dropout": 0.1,
            "lr": trial.suggest_float("lr", 1e-4, 5e-3, log=True),
            "n_epochs": 10, 
            "early_stop": 5,
            "batch_size": 1024,
            "GPU": GPU_ID,
            "seed": 42,
        }
        
        model_config = {
            "class": MODEL_CLASS,
            "module_path": MODEL_MODULE,
            "kwargs": params,
        }
        
        model = init_instance_by_config(model_config)
        # fit() on ALSTM_TS handles the TSDatasetH correctly
        model.fit(dataset)
        
        # TS-compatible predict/prepare
        pred = model.predict(dataset, segment="valid")
        # Get labels directly from handler for the same segment and align with pred's index
        label_df = dataset.handler.fetch(dataset.segments["valid"], col_set="label")
        
        # Align label with pred index (both are <datetime, instrument>)
        label_series = label_df.reindex(pred.index).iloc[:, 0]
        
        pred_val = pred.values
        label_val = label_series.values
        
        mask = ~np.isnan(label_val)
        if len(label_val[mask]) == 0:
            return 1e10
            
        mse = ((pred_val[mask] - label_val[mask]) ** 2).mean()
        logger.info(f"Trial {trial.number} finished with MSE: {mse:.8f}")
        return mse

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=N_TRIALS)

    logger.info(f"Best parameters found: {study.best_params}")

    # 5. Train Best Model & Predict
    logger.info(f"Step 3: Training Final {MODEL_CLASS} Model")
    best_params = study.best_params
    best_params.update({
        "d_feat": alstm_d_feat,
        "n_epochs": 30, 
        "early_stop": 10,
        "batch_size": 1024,
        "GPU": GPU_ID,
        "seed": 42,
    })

    best_model_config = {
        "class": MODEL_CLASS,
        "module_path": MODEL_MODULE,
        "kwargs": best_params,
    }

    best_model = init_instance_by_config(best_model_config)
    best_model.fit(dataset)

    test_pred = best_model.predict(dataset, segment="test")
    # Fetch labels from handler and align with pred index
    test_label_df = dataset.handler.fetch(dataset.segments["test"], col_set="label")
    test_label = test_label_df.reindex(test_pred.index).iloc[:, 0]

    # 6. Visualization
    logger.info("Step 4: Visualizing Results")
    
    try:
        pred_series = test_pred.xs(SYMBOL, level='instrument')
        label_series = test_label.xs(SYMBOL, level='instrument')
    except (KeyError, ValueError, TypeError):
        level = 1 if test_pred.index.nlevels > 1 else 0
        pred_series = test_pred.xs(SYMBOL, level=level)
        label_series = test_label.xs(SYMBOL, level=level)

    raw_close_df = D.features(market, ["$close"], 
                           start_time=TEST_START,
                           end_time=TEST_END,
                           freq=FREQ)
    actual_price = raw_close_df.xs(SYMBOL, level='instrument')['$close']
    
    common_idx = actual_price.index.intersection(pred_series.index)
    actual_price = actual_price.loc[common_idx]
    pred_return = pred_series.loc[common_idx]
    
    predicted_price = actual_price * (1 + pred_return)
    
    plot_df = pd.DataFrame({
        "Actual Price": actual_price.shift(-1),
        "Predicted Price": predicted_price
    }).dropna()

    plt.figure(figsize=(15, 7))
    plt.plot(plot_df.index[:PLOT_RANGE], plot_df["Actual Price"].iloc[:PLOT_RANGE], label="Actual Close Price", alpha=0.8)
    plt.plot(plot_df.index[:PLOT_RANGE], plot_df["Predicted Price"].iloc[:PLOT_RANGE], label="Predicted Price", alpha=0.8, linestyle='--')
    plt.title(f"{SYMBOL} Price Prediction - {MODEL_CLASS} + Alpha360")
    plt.xlabel("Datetime")
    plt.ylabel("Price (USDT)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("examples/price_prediction_alstm.png")
    logger.info("Price plot saved to examples/price_prediction_alstm.png")

    # 7. QUANTITATIVE EVALUATION METRICS
    logger.info("Step 5: Quantitative Evaluation")
    eval_df = pd.DataFrame({
        "pred": pred_series.values,
        "label": label_series.values.flatten()
    }).dropna()

    if len(eval_df) > 0:
        ic, _ = pearsonr(eval_df["pred"], eval_df["label"])
        rank_ic, _ = spearmanr(eval_df["pred"], eval_df["label"])
        same_dir = ((eval_df["pred"] > 0) == (eval_df["label"] > 0)).sum()
        acc = same_dir / len(eval_df)
        rmse = np.sqrt(((eval_df["pred"] - eval_df["label"]) ** 2).mean())
        mae = np.abs(eval_df["pred"] - eval_df["label"]).mean()

        report = f"""
==================================================
FINAL MODEL EVALUATION REPORT (TEST SET)
==================================================
Symbol:                {SYMBOL}
Model:                 {MODEL_CLASS}
Data Handler:          {DATA_HANDLER_CLASS}
--------------------------------------------------
IC (Pearson Corr):     {ic:.4f}
Rank IC (Spearman):    {rank_ic:.4f}
Directional Accuracy:  {acc:.2%}
MAE:                   {mae:.6f}
RMSE:                  {rmse:.6f}
--------------------------------------------------
Total test samples:    {len(eval_df)}
Positive Predictions:  {(eval_df["pred"] > 0).sum()} ({(eval_df["pred"] > 0).sum()/len(eval_df):.2%})
Actual Positive:       {(eval_df["label"] > 0).sum()} ({(eval_df["label"] > 0).sum()/len(eval_df):.2%})
==================================================
"""
        logger.info(report)
        
        if ic > 0.05:
            logger.info("-> [GOOD] The model shows significant predictive alpha.")
        elif ic > 0:
            logger.info("-> [WEAK] Positive correlation detected, but difficult to trade.")
        else:
            logger.warning("-> [POOR] Negative or zero correlation. Model needs more features/tuning.")
    else:
        logger.error("No valid samples in test set for evaluation.")

    logger.info("Test completed.")

if __name__ == "__main__":
    run_model_test()
