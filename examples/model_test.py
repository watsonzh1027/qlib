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
import argparse

# ==============================================================================
# 1. PARAMETERS - SUPPORTS CLI OVERRIDE
# ==============================================================================
parser = argparse.ArgumentParser()
parser.add_argument("--symbol", type=str, default="eth_usdt_4h_future")
parser.add_argument("--freq", type=str, default="1h")
parser.add_argument("--n_trials", type=int, default=10)
parser.add_argument("--vol_scale", action="store_true")
parser.add_argument("--n_jobs", type=int, default=4)
parser.add_argument("--train_start", type=str, default="2020-01-01")
parser.add_argument("--test_start", type=str, default="2025-01-01")
args = parser.parse_args()

PROVIDER_URI = "data/qlib_data/crypto"
SYMBOL = args.symbol
FREQ = args.freq
N_TRIALS = args.n_trials

# Data Configuration
DATA_HANDLER_CLASS = "DataHandlerLP" 
DATA_HANDLER_MODULE = "qlib.data.dataset.handler"
TS_STEP_LEN = 20
CORR_THRESHOLD = 0.98

# Model Configuration
MODEL_CLASS = "ALSTM"
MODEL_MODULE = "qlib.contrib.model.pytorch_alstm_ts"

# Time Range
# Time Range from Args
TRAIN_START = args.train_start
TEST_START = args.test_start

# Deriving other ranges automatically
# Training usually ends when test/validation starts
# We can set a standard validation period (e.g. 6 months before test)
TRAIN_END = (pd.to_datetime(TEST_START) - pd.Timedelta(days=180)).strftime("%Y-%m-%d")
VALID_START = (pd.to_datetime(TRAIN_END) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
VALID_END = (pd.to_datetime(TEST_START) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

START_TIME = TRAIN_START
END_TIME = "2026-01-01" 
TEST_END = "2025-12-31"

GPU_ID = 0 if torch.cuda.is_available() else -1
# ==============================================================================

def drop_correlated_features(df, threshold=0.98, logger=None):
    """Identifies and drops highly correlated features and constant features."""
    if logger:
        logger.info(f"Checking redundant features with threshold {threshold}...")
    constant_features = [col for col in df.columns if df[col].std() == 0]
    if constant_features:
        df = df.drop(columns=constant_features)
    corr_matrix = df.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    to_drop = [column for column in upper.columns if any(upper[column] > threshold)]
    return df.drop(columns=to_drop), to_drop

def run_model_test():
    setup_logging()
    logger = get_logger("model_test")
    
    # 1. Initialize Qlib
    qlib.init(provider_uri=PROVIDER_URI, region=qlib.config.REG_CN)
    
    # 2. Hybrid Feature Config
    f158, n158 = Alpha158DL.get_feature_config()
    f360, n360 = Alpha360DL.get_feature_config()
    hybrid_features = f158 + f360
    hybrid_names = [f"A158_{n}" for n in n158] + [f"A360_{n}" for n in n360]
    
    # 3. Label Config
    label_cfg = ["Ref($close, -1)/$close - 1"]
    if args.vol_scale:
        label_cfg = ["(Ref($close, -1)/$close - 1) / (Std(Ref($close, -1)/$close - 1, 20) + 1e-6)"]
        logger.info("Enabling Volatility Scaling for labels.")

    handler_kwargs = {
        "class": DATA_HANDLER_CLASS,
        "module_path": DATA_HANDLER_MODULE,
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
        },
    }

    dataset_config = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": handler_kwargs,
            "segments": {"train": (TRAIN_START, TRAIN_END), "valid": (VALID_START, VALID_END), "test": (TEST_START, TEST_END)},
        },
    }

    logger.info(f"Step 1: Qlib initialized for {SYMBOL} at {FREQ}.")
    
    try:
        dataset_init = init_instance_by_config(dataset_config)
        df_train_init = dataset_init.prepare("train", col_set="feature")
        df_train_filtered, to_drop = drop_correlated_features(df_train_init, threshold=CORR_THRESHOLD, logger=logger)
        
        remaining_indices = [i for i, name in enumerate(hybrid_names) if name not in to_drop]
        final_features = [hybrid_features[i] for i in remaining_indices]
        final_names = [hybrid_names[i] for i in remaining_indices]
        
        handler_kwargs["kwargs"]["data_loader"]["kwargs"]["config"]["feature"] = (final_features, final_names)
        dataset_config["class"] = "TSDatasetH"
        dataset_config["kwargs"]["handler"] = handler_kwargs
        dataset_config["kwargs"]["step_len"] = TS_STEP_LEN
        dataset = init_instance_by_config(dataset_config)
        
        # Get feature dimension
        d_feat = len(final_names)
        logger.info(f"Feature dimension: {d_feat}")

        # 4. Optuna Optimization
        def objective(trial):
            params = {
                "d_feat": d_feat,
                "rnn_type": "LSTM",
                "hidden_size": trial.suggest_int("hidden_size", 64, 256),
                "num_layers": trial.suggest_int("num_layers", 1, 3),
                "dropout": trial.suggest_float("dropout", 0.1, 0.5),
                "lr": trial.suggest_float("lr", 1e-5, 1e-3, log=True),
                "batch_size": 2048, "n_epochs": 30, "early_stop": 10, "GPU": GPU_ID, "n_jobs": args.n_jobs,
            }
            try:
                model = init_instance_by_config({"class": MODEL_CLASS, "module_path": MODEL_MODULE, "kwargs": params})
                model.fit(dataset)
                valid_pred = model.predict(dataset, segment="valid")
                valid_label = dataset.handler.fetch(valid_pred.index, col_set="label")
                mse = ((valid_pred - valid_label.iloc[:, 0])**2).dropna().mean()
                return float(mse) if not np.isnan(mse) else 9999.0
            except Exception as e:
                logger.warning(f"Trial failed with error: {e}")
                return 9999.0

        logger.info(f"Step 2: Starting Optuna ({N_TRIALS} trials)...")
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=N_TRIALS)
        
        best_params = study.best_params
        best_params.update({
            "d_feat": d_feat,
            "rnn_type": "LSTM",
            "batch_size": 2048,
            "n_epochs": 50,
            "early_stop": 15,
            "GPU": GPU_ID,
            "n_jobs": args.n_jobs
        })
        
        # 5. Final Model
        logger.info("Step 3: Training final model...")
        model = init_instance_by_config({"class": MODEL_CLASS, "module_path": MODEL_MODULE, "kwargs": best_params})
        model.fit(dataset)

        # 6. Evaluation
        logger.info("Step 4: Model Evaluation (Test Set)...")
        test_pred = model.predict(dataset, segment="test")
        test_label = dataset.handler.fetch(test_pred.index, col_set="label").iloc[:, 0]
        
        ic = pearsonr(test_pred, test_label)[0]
        rank_ic = spearmanr(test_pred, test_label)[0]
        acc = ((test_pred > 0) == (test_label > 0)).mean()
        
        report = f"""
==================================================
FINAL MODEL EVALUATION REPORT (TEST SET)
==================================================
Symbol:                {SYMBOL}
Frequency:             {FREQ}
Vol Scaling:           {args.vol_scale}
--------------------------------------------------
IC (Pearson Corr):     {ic:.4f}
Rank IC (Spearman):    {rank_ic:.4f}
Directional Accuracy:  {acc:.2%}
Total test samples:    {len(test_label)}
==================================================
"""
        logger.info(report)
        print(report) # Ensure stdout capture
        plt.figure(figsize=(15, 6))
        plt.plot(test_label.values[:200], label="Actual Return", alpha=0.5)
        plt.plot(test_pred.values[:200], label="Predicted", color='red')
        plt.title(f"Result - {SYMBOL} ({FREQ})")
        plt.savefig(f"examples/prediction_{SYMBOL}_{FREQ}_{'vol' if args.vol_scale else 'norm'}.png")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        import sys
        sys.stderr.write(traceback.format_exc())

if __name__ == "__main__":
    run_model_test()
