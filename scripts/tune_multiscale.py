
import optuna
import json
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from qlib.data.dataset import DatasetH
from qlib.workflow import R
import sys

# Add project root to path
CUR_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.train_multiscale import MultiScaleTrainer

class MultiScaleTuner:
    def __init__(self, config_path="config/workflow_multiscale.json"):
        self.trainer = MultiScaleTrainer(config_path)
        self.best_params = {}

    def objective(self, trial, timeframe, model_type="lgb"):
        # Suggest parameters based on model type
        if model_type == "lgb":
            model_params = {
                "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.1, log=True),
                "num_leaves": trial.suggest_int("num_leaves", 16, 256),
                "max_depth": trial.suggest_int("max_depth", 3, 12),
                "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
                "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
                "bagging_freq": trial.suggest_int("bagging_freq", 1, 7),
                "lambda_l1": trial.suggest_float("lambda_l1", 1e-8, 10.0, log=True),
                "lambda_l2": trial.suggest_float("lambda_l2", 1e-8, 10.0, log=True),
                "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 10, 100),
            }
        elif model_type == "xgb":
            model_params = {
                "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                "subsample": trial.suggest_float("subsample", 0.5, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
                "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
                "gamma": trial.suggest_float("gamma", 1e-8, 1.0, log=True),
            }
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        # Serialize params
        import json
        params_json = json.dumps(model_params)
        
        # Call train script via subprocess
        import subprocess
        import re
        
        cmd = [
            sys.executable, 
            "scripts/train_multiscale.py", 
            "--timeframe", str(timeframe),
            "--model", model_type,
            "--params", params_json,
            "--eval_ic"
        ]
        
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            # Find IC
            match = re.search(r"IC: ([-\d\.]+)", output)
            if match:
                ic = float(match.group(1))
                if np.isnan(ic):
                    return -9999.0
                return ic
            else:
                print(f"IC not found in output for trial {trial.number}")
                with open("debug_output.log", "w") as f:
                     f.write(output)
                print("Written debug_output.log")
                return -9999.0
                
        except subprocess.CalledProcessError as e:
            print(f"Trial fail env: {e.output[-500:]}")
            return -9999.0

    def run_tuning(self, timeframe, n_trials=20, model_type="lgb"):
        print(f"Starting tuning for {timeframe} with {n_trials} trials (model: {model_type})...")
        study = optuna.create_study(direction="maximize")
        study.optimize(lambda t: self.objective(t, timeframe, model_type), n_trials=n_trials)
        
        print("\nBest params:")
        print(study.best_params)
        print(f"Best IC: {study.best_value}")
        
        self.best_params[timeframe] = study.best_params
        
        # Save best params to json
        out_file = Path(f"config/tuned_params_{timeframe}_{model_type}.json")
        with open(out_file, "w") as f:
            json.dump(study.best_params, f, indent=4)
        print(f"Saved tuned params to {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", type=str, required=True, help="Timeframe to tune (e.g., 15min, 60min)")
    parser.add_argument("--model", type=str, default="lgb", choices=["lgb", "xgb"], help="Model type")
    parser.add_argument("--n_trials", type=int, default=10, help="Number of trials")
    args = parser.parse_args()
    
    tuner = MultiScaleTuner()
    tuner.run_tuning(args.timeframe, args.n_trials, args.model)
