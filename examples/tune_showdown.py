import qlib
import pandas as pd
import numpy as np
import optuna
import torch
from qlib.utils import init_instance_by_config
from qlib.contrib.data.loader import Alpha158DL, Alpha360DL
from qlib.log import get_module_logger
import argparse

# ==============================================================================
# PARAMETERS
# ==============================================================================
SYMBOL = "eth_usdt_4h_future"
FREQ = "240min"
PROVIDER_URI = "data/qlib_data/crypto"

# Time Range
TRAIN_START = "2023-01-01"
TEST_START = "2025-01-01"
TRAIN_END = (pd.to_datetime(TEST_START) - pd.Timedelta(days=120)).strftime("%Y-%m-%d")
VALID_START = (pd.to_datetime(TRAIN_END) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
VALID_END = (pd.to_datetime(TEST_START) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
START_TIME = TRAIN_START
END_TIME = "2026-01-01" 
TEST_END = "2025-12-31"

def get_data_config(use_ts=False):
    f158, n158 = Alpha158DL.get_feature_config()
    f360, n360 = Alpha360DL.get_feature_config()
    hybrid_features = f158 + f360 + ["$weekday", "$hour"]
    hybrid_names = [f"A158_{n}" for n in n158] + [f"A360_{n}" for n in n360] + ["weekday", "hour"]
    
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
        dataset_conf["kwargs"]["step_len"] = 30
        
    return dataset_conf, len(hybrid_features)

def tune_lgbm(n_trials=20):
    logger = get_module_logger("tune_lgbm")
    dataset_conf, _ = get_data_config(use_ts=False)
    dataset = init_instance_by_config(dataset_conf)

    def objective(trial):
        params = {
            "loss": "mse",
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 31, 512),
            "max_depth": trial.suggest_int("max_depth", 3, 12),
             "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
            "verbosity": -1,
            "num_threads": 8
        }
        model_conf = {
            "class": "LGBModel",
            "module_path": "qlib.contrib.model.gbdt",
            "kwargs": params
        }
        model = init_instance_by_config(model_conf)
        model.fit(dataset)
        
        pred = model.predict(dataset, segment="valid")
        label = dataset.handler.fetch(pred.index, col_set="label")
        if isinstance(label, pd.DataFrame):
            label = label.iloc[:, 0]
        
        # We use IC as the objective to maximize
        combined = pd.concat([pred, label], axis=1).dropna()
        if len(combined) < 10:
            return -1.0
        ic = combined.corr().iloc[0, 1]
        return ic

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)
    
    logger.info(f"Best LGBM IC: {study.best_value}")
    logger.info(f"Best LGBM Params: {study.best_params}")
    return study.best_params

def tune_alstm(n_trials=10):
    logger = get_module_logger("tune_alstm")
    dataset_conf, d_feat = get_data_config(use_ts=True)
    dataset = init_instance_by_config(dataset_conf)

    def objective(trial):
        params = {
            "d_feat": d_feat,
            "hidden_size": trial.suggest_int("hidden_size", 64, 256),
            "num_layers": trial.suggest_int("num_layers", 1, 3),
            "dropout": trial.suggest_float("dropout", 0.1, 0.5),
            "lr": trial.suggest_float("lr", 1e-5, 1e-3, log=True),
            "batch_size": 1024,
            "n_epochs": 20,
            "early_stop": 5,
            "GPU": 0 if torch.cuda.is_available() else -1,
        }
        model_conf = {
            "class": "ALSTM",
            "module_path": "qlib.contrib.model.pytorch_alstm_ts",
            "kwargs": params
        }
        try:
            model = init_instance_by_config(model_conf)
            model.fit(dataset)
            pred = model.predict(dataset, segment="valid")
            label = dataset.handler.fetch(pred.index, col_set="label")
            if isinstance(label, pd.DataFrame):
                label = label.iloc[:, 0]
            combined = pd.concat([pred, label], axis=1).dropna()
            if len(combined) < 10:
                return -1.0
            ic = combined.corr().iloc[0, 1]
            return ic
        except Exception as e:
            logger.warning(f"ALSTM trial failed: {e}")
            return -1.0

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)
    
    logger.info(f"Best ALSTM IC: {study.best_value}")
    logger.info(f"Best ALSTM Params: {study.best_params}")
    return study.best_params

if __name__ == "__main__":
    qlib.init(provider_uri=PROVIDER_URI)
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, choices=["lgbm", "alstm", "both"], default="both")
    parser.add_argument("--trials", type=int, default=10)
    args = parser.parse_args()
    
    if args.model in ["lgbm", "both"]:
        tune_lgbm(n_trials=args.trials)
    
    if args.model in ["alstm", "both"]:
        tune_alstm(n_trials=args.trials)
