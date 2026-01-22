import sys
from pathlib import Path
import json
import argparse
import pickle
import copy
import pandas as pd
import qlib
from qlib.data import D
from qlib.config import REG_CN
from qlib.utils import init_instance_by_config
from qlib.contrib.model.gbdt import LGBModel
from datetime import datetime

# Add project root to path
CUR_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

class MultiScaleTrainer:
    def __init__(self, config_path="config/workflow_multiscale.json", model_params_override=None, n_jobs=4, model_type=None):
        self.config_path = config_path
        self.n_jobs = n_jobs
        with open(config_path, "r") as f:
            self.config = json.load(f)
        
        # Set model type
        self.model_type = model_type or self.config.get("model_type", "lgb")
        print(f"Using model type: {self.model_type}")
            
        if model_params_override:
            print(f"Overriding model params with: {model_params_override}")
            param_key = f"{self.model_type}_params"
            if param_key in self.config:
                self.config[param_key].update(model_params_override)
            else:
                self.config[param_key] = model_params_override
        
        # Init Qlib removed from here, done per model
        
        self.model_dir = Path("models/multiscale")
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def train_model(self, timeframe, tf_config, eval_ic=False):
        print(f"\n{'='*20} Training Model for Timeframe: {timeframe} {'='*20}")
        
        # Init Qlib for this timeframe
        provider_uri = f"data/qlib_data/crypto_{timeframe}"
        if not Path(provider_uri).exists():
             print(f"Data directory {provider_uri} not found. Skipping.")
             return None

        qlib.init(provider_uri=provider_uri, region=REG_CN)

        # 1. Prepare Data Handler Config
        dh_config = copy.deepcopy(self.config["data_handler_config"])
        
        # Update freq and label specific to this timeframe
        dh_config["freq"] = tf_config["freq"]
        dh_config["instruments"] = ["ETH_USDT"] # Simple name now
        
        # Construct label config
        dh_config["label"] = tf_config["label"]

        handler_class = "Alpha158"
        handler_module = "qlib.contrib.data.handler"

        custom_features = self.config.get("custom_features", [])
        if custom_features:
            print(f"Injecting {len(custom_features)} custom features...")
            # Lazy import to avoid top-level dependency if not needed
            from qlib.contrib.data.loader import Alpha158DL
            f158, n158 = Alpha158DL.get_feature_config()
            
            hybrid_features = f158 + custom_features
            # Simple naming for custom features
            hybrid_names = n158 + [f"custom_{i}" for i in range(len(custom_features))]
            
            # Switch to generic DataHandlerLP
            handler_class = "DataHandlerLP"
            handler_module = "qlib.data.dataset.handler"
            
            # Explicitly define data loader
            dh_config["data_loader"] = {
                "class": "QlibDataLoader",
                "kwargs": {
                    "config": {
                        "feature": (hybrid_features, hybrid_names),
                        "label": (dh_config["label"], ["LABEL"]),
                    },
                    "freq": dh_config["freq"],
                },
            }
        
        try:
            cal = D.calendar(freq=timeframe)
            if len(cal) == 0:
                print(f"No data found for freq {timeframe}")
                return None
            
            # Ensure naive timestamps for comparison
            start_date = pd.Timestamp(cal[0]).tz_localize(None)
            end_date = pd.Timestamp(cal[-1]).tz_localize(None)
            print(f"Data available for {timeframe}: {start_date} to {end_date}")
            
            # Use config fit_start_time/end_time as boundaries
            cfg_start = pd.Timestamp(dh_config.get("fit_start_time", "2010-01-01")).tz_localize(None)
            cfg_end = pd.Timestamp(dh_config.get("fit_end_time", "2099-12-31")).tz_localize(None)
            
            real_start = max(start_date, cfg_start)
            real_end = min(end_date, cfg_end)
            
            if real_start >= real_end:
                print(f"Configured time range {cfg_start}-{cfg_end} is outside available data {start_date}-{end_date}")
                return None
 
            # Split logic: last 20% for valid+test
            total_days = (real_end - real_start).days
            train_end = real_start + pd.Timedelta(days=int(total_days * 0.8))
            valid_end = real_start + pd.Timedelta(days=int(total_days * 0.9))
            
            fmt = "%Y-%m-%d %H:%M:%S"
            segments = {
                "train": (real_start.strftime(fmt), train_end.strftime(fmt)),
                "valid": ((train_end + pd.Timedelta(days=1)).strftime(fmt), valid_end.strftime(fmt)),
                "test": ((valid_end + pd.Timedelta(days=1)).strftime(fmt), real_end.strftime(fmt))
            }
            
            print(f"Auto-split segments for {timeframe}:")
            for k, v in segments.items():
                print(f"  {k}: {v[0]} to {v[1]}")
            
            # Update handler config
            sd_str = real_start.strftime(fmt)
            ed_str = real_end.strftime(fmt)
            dh_config["start_time"] = sd_str
            dh_config["end_time"] = ed_str
            dh_config["fit_start_time"] = sd_str
            dh_config["fit_end_time"] = segments["train"][1] # Fit only on train!

            # Patch processors with fit times
            for proc_key in ["infer_processors", "learn_processors"]:
                if proc_key in dh_config:
                    for proc in dh_config[proc_key]:
                        if proc["class"] == "RobustZScoreNorm":
                            proc.setdefault("kwargs", {})
                            proc["kwargs"]["fit_start_time"] = dh_config["fit_start_time"]
                            proc["kwargs"]["fit_end_time"] = dh_config["fit_end_time"]
            
            # Remove keys that are not accepted by DataHandlerLP
            dh_config.pop("fit_start_time", None)
            dh_config.pop("fit_end_time", None)
            dh_config.pop("freq", None)
            dh_config.pop("label", None)

        except Exception as e:
            print(f"Error calculating calendar: {e}")
            import traceback
            traceback.print_exc()
            return None

        dataset_config = {
            "class": "DatasetH",
            "module_path": "qlib.data.dataset",
            "kwargs": {
                "handler": {
                    "class": handler_class,
                    "module_path": handler_module,
                    "kwargs": dh_config
                },
                "segments": segments
            }
        }
        
        print(f"Initializing Dataset for {timeframe}...")
        try:
            dataset = init_instance_by_config(dataset_config)
        except Exception as e:
            print(f"Error initializing dataset for {timeframe}: {e}")
            return None

        # 2. Init Model
        if self.model_type == "lgb":
            model_kwargs = {
                "loss": "mse",
                "num_threads": self.n_jobs,
                **self.config.get("lgb_params", {})
            }
            if self.n_jobs is not None:
                model_kwargs["num_threads"] = self.n_jobs
            model_config = {
                "class": "LGBModel",
                "module_path": "qlib.contrib.model.gbdt",
                "kwargs": model_kwargs
            }
        elif self.model_type == "xgb":
            model_kwargs = self.config.get("xgb_params", {}).copy()
            if self.n_jobs is not None:
                model_kwargs["nthread"] = self.n_jobs
            model_config = {
                "class": "XGBModel",
                "module_path": "qlib.contrib.model.xgboost",
                "kwargs": model_kwargs
            }
        elif self.model_type == "alstm":
            alstm_params = self.config.get("alstm_params", {}).copy()
            # Update d_feat based on actual feature count if custom features exist
            custom_features = self.config.get("custom_features", [])
            if custom_features:
                alstm_params["d_feat"] = 158 + len(custom_features)
            model_config = {
                "class": "ALSTM",
                "module_path": "qlib.contrib.model.pytorch_alstm",
                "kwargs": alstm_params
            }
        elif self.model_type == "lstm":
            lstm_params = self.config.get("lstm_params", {}).copy()
            # SimpleLSTM works with Alpha158 features directly
            # d_feat should be the total number of features (162)
            custom_features = self.config.get("custom_features", [])
            if custom_features:
                lstm_params["d_feat"] = 158 + len(custom_features)
            else:
                lstm_params["d_feat"] = 162
            model_config = {
                "class": "SimpleLSTM",
                "module_path": "qlib.contrib.model.simple_lstm",
                "kwargs": lstm_params
            }
        elif self.model_type == "catboost":
            catboost_params = self.config.get("catboost_params", {}).copy()
            model_config = {
                "class": "CatBoostModel",
                "module_path": "qlib.contrib.model.catboost_model",
                "kwargs": catboost_params
            }
        elif self.model_type == "mlp":
            mlp_params = self.config.get("mlp_params", {}).copy()
            custom_features = self.config.get("custom_features", [])
            if custom_features:
                mlp_params["d_feat"] = 158 + len(custom_features)
            else:
                mlp_params["d_feat"] = 162
            model_config = {
                "class": "MLP",
                "module_path": "qlib.contrib.model.mlp",
                "kwargs": mlp_params
            }
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
        
        model = init_instance_by_config(model_config)
        
        # 3. Train
        print(f"Starts training {timeframe} {self.model_type.upper()} model...")
        model.fit(dataset)
        
        # 4. Save
        save_path = self.model_dir / f"model_{timeframe}_{self.model_type}.bin"
        with open(save_path, "wb") as f:
            pickle.dump(model, f)
        
        print(f"Model saved to {save_path}")
        
        if eval_ic:
            try:
                print("Evaluating IC on 'valid' set...")
                # Use 'valid' segment
                # Force data loading? infer mode
                pred = model.predict(dataset, segment="valid")
                if isinstance(pred, pd.Series):
                    pred_df = pred.to_frame("score")
                else:
                    # In case it's numpy array, need index from dataset?
                    # dataset.prepare returns (features, label)
                    # We can get index from `dataset.prepare("valid")[1].index` but expensive
                    # Assuming predict returns Series usually if dataset is DatasetH
                    pred_df = pd.DataFrame(pred, columns=["score"])

                # Fetch just the label
                # Note: prepare might return DF or tuple depending on arg
                # Let's try separate calls
                label = dataset.prepare("valid", col_set=["label"], data_key="infer")
                if isinstance(label, tuple) or isinstance(label, list):
                     label = label[0] # Assume first item
                
                print(f"Label shape: {label.shape}")
                
                 # Align predictions to label
                if not isinstance(pred_df.index, pd.MultiIndex):
                     if hasattr(label, 'index'):
                        pred_df.index = label.index
                    
                combined = pd.concat([pred_df, label], axis=1).dropna()
                if not combined.empty:
                    ic = combined.iloc[:, 0].corr(combined.iloc[:, 1])
                    print(f"IC: {ic}")
                else:
                    print(f"IC: NaN (Empty combined)")
            except Exception as e:
                print(f"Error evaluating IC: {e}")
                import traceback
                traceback.print_exc()

        return model, dataset

    def run(self, specific_timeframe=None, eval_ic=False):
        timeframes = self.config["timeframes"]
        
        # Filter if specific timeframe requested
        if specific_timeframe:
            if specific_timeframe not in timeframes:
                raise ValueError(f"Timeframe {specific_timeframe} not found in config.")
            target_tfs = {specific_timeframe: timeframes[specific_timeframe]}
        else:
            target_tfs = timeframes

        for tf_name, tf_config in target_tfs.items():
            self.train_model(tf_name, tf_config, eval_ic=eval_ic)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", type=str, help="Specific timeframe to train (e.g. 60min)")
    parser.add_argument("--params", type=str, help="JSON string of model params override")
    parser.add_argument("--model", type=str, choices=["lgb", "xgb", "alstm", "lstm", "catboost", "mlp"], help="Model type")
    parser.add_argument("--n_jobs", type=int, default=4, help="Number of threads for tree models")
    parser.add_argument("--eval_ic", action="store_true", help="Evaluate and print IC")
    
    args = parser.parse_args()
    
    params_override = None
    if args.params:
        try:
            params_override = json.loads(args.params)
        except json.JSONDecodeError as e:
            print(f"Error parsing params JSON: {e}")
            sys.exit(1)
    
    trainer = MultiScaleTrainer(model_params_override=params_override, n_jobs=args.n_jobs, model_type=args.model)
    trainer.run(specific_timeframe=args.timeframe, eval_ic=args.eval_ic)
