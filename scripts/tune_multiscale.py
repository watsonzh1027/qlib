
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

    def objective(self, trial, timeframe):
        # Suggest parameters
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
                # print(output[-500:]) # Check end of output
                return -9999.0
                
        except subprocess.CalledProcessError as e:
            print(f"Trial fail env: {e.output[-500:]}")
            return -9999.0

    def run_tuning(self, timeframe, n_trials=20):
        print(f"Starting tuning for {timeframe} with {n_trials} trials...")
        study = optuna.create_study(direction="maximize")
        study.optimize(lambda t: self.objective(t, timeframe), n_trials=n_trials)
        
        print("\nBest params:")
        print(study.best_params)
        print(f"Best IC: {study.best_value}")
        
        self.best_params[timeframe] = study.best_params
        
        # Save best params to json
        out_file = Path(f"config/tuned_params_{timeframe}.json")
        with open(out_file, "w") as f:
            json.dump(study.best_params, f, indent=4)
        print(f"Saved tuned params to {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", type=str, required=True, help="Timeframe to tune (e.g., 15min, 60min)")
    parser.add_argument("--n_trials", type=int, default=10, help="Number of trials")
    args = parser.parse_args()
    
    tuner = MultiScaleTuner()
    tuner.run_tuning(args.timeframe, args.n_trials)
