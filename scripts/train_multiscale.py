import sys
from pathlib import Path
import json
import argparse
import pickle
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
    def __init__(self, config_path="config/workflow_multiscale.json", model_params_override=None):
        self.config_path = config_path
        with open(config_path, "r") as f:
            self.config = json.load(f)
            
        if model_params_override:
            print(f"Overriding model params with: {model_params_override}")
            self.config["model_params"].update(model_params_override)
        
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
        dh_config = self.config["data_handler_config"].copy()
        
        # Update freq and label specific to this timeframe
        dh_config["freq"] = tf_config["freq"]
        dh_config["instruments"] = ["ETH_USDT"] # Simple name now
        
        # Construct label config
        dh_config["label"] = tf_config["label"]
        
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
                    "class": "Alpha158",
                    "module_path": "qlib.contrib.data.handler",
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
        model_config = {
            "class": "LGBModel",
            "module_path": "qlib.contrib.model.gbdt",
            "kwargs": {
                "loss": "mse",
                "num_threads": 4,
                **self.config["model_params"]
            }
        }
        model = init_instance_by_config(model_config)
        
        # 3. Train
        print(f"Starts training {timeframe} model...")
        model.fit(dataset)
        
        # 4. Save
        save_path = self.model_dir / f"model_{timeframe}.bin"
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
    parser.add_argument("--eval_ic", action="store_true", help="Evaluate and print IC")
    
    args = parser.parse_args()
    
    params_override = None
    if args.params:
        try:
            params_override = json.loads(args.params)
        except json.JSONDecodeError as e:
            print(f"Error parsing params JSON: {e}")
            sys.exit(1)
    
    trainer = MultiScaleTrainer(model_params_override=params_override)
    trainer.run(specific_timeframe=args.timeframe, eval_ic=args.eval_ic)
