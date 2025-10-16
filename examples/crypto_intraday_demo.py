"""
Minimal intraday demo using CryptoTopNStrategy (1h interval).

Notes:
- This demo expects that you have 1h (or higher-frequency) data available in qlib's provider_uri.
- If you don't have 1h data, the script will attempt to run but may fail when preparing dataset.
"""
import qlib
import runpy
import os
import sys
from pathlib import Path

# Add project root to path to allow imports from scripts
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from qlib.constant import REG_CN
from qlib.utils import init_instance_by_config, flatten_dict
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, PortAnaRecord, SigAnaRecord
from qlib.tests.data import GetData
from qlib.contrib.strategy import CryptoTopNStrategy
from qlib.data import D

# Import crypto collector with better error handling
try:
    from scripts.data_collector.crypto import collector as cc
except ImportError as e:
    try:
        # Try installing required dependencies
        import subprocess
        print("Installing required dependencies...")
        subprocess.check_call([
            "pip", "install", "-r", 
            str(PROJECT_ROOT / "scripts" / "data_collector" / "crypto" / "requirements.txt")
        ])
        from scripts.data_collector.crypto import collector as cc
    except Exception as e2:
        print(f"Failed to import and install crypto collector: {e2}")
        print("Please install dependencies manually:")
        print("pip install -r scripts/data_collector/crypto/requirements.txt")
        sys.exit(1)


def main():
    # Use absolute path for provider_uri
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    provider_uri = str(current_dir.parent / "data" / "crypto_1h")
    
    # Ensure the provider directory exists
    os.makedirs(provider_uri, exist_ok=True)

    # Attempt to download & normalize crypto 1h data
    try:
        print("Starting crypto data download/normalize (1h) into:", provider_uri)
        source_dir = os.path.join(provider_uri, "source")
        os.makedirs(source_dir, exist_ok=True)
        normalize_dir = os.path.join(provider_uri, "normalize")
        os.makedirs(normalize_dir, exist_ok=True)
        
        start = "2025-01-01"  # Updated to match the query period
        end = "2025-10-05"    # Updated to match the query period
        limit_nums = 5        # limit to 5 symbols for quick demo

        collector = cc.CryptoCollector(
            save_dir=source_dir,
            start=start,
            end=end,
            interval="1h",
            max_workers=2,
            max_collector_count=2,
            delay=1,
            limit_nums=limit_nums
        )
        collector.collector_data()

        # normalize into normalize_dir
        import glob
        import shutil

        # Find all CSV files in source_dir
        source_files = glob.glob(os.path.join(source_dir, "*.csv"))
        if not source_files:
            print(f"No CSV files found in {source_dir} for normalization.")
            return

        import pandas as pd
        for src_file in source_files:
            df = None
            try:
                df = pd.read_csv(src_file)
                print(f"Successfully loaded {src_file} with columns: {df.columns.tolist()}")
            except Exception as e:
                print(f"Failed to read {src_file}: {e}")
                continue
            norm_obj = cc.CryptoNormalize(source_dir, normalize_dir, max_workers=2)
            try:
                norm_df = norm_obj.normalize(df)
                print(f"Successfully normalized {src_file}")
            except Exception as e:
                print(f"Failed to normalize {src_file}: {e}")
                continue
            # Save normalized file to normalize_dir
            norm_file = os.path.join(normalize_dir, os.path.basename(src_file))
            norm_df.to_csv(norm_file, index=False)

        # dump into qlib format
        import subprocess
        dump_cmd = [
            "python", "./scripts/dump_bin.py", "dump_all",
            "--data_path", normalize_dir,
            "--qlib_dir", provider_uri,
            "--freq", "1h",
            "--date_field_name", "date",
            "--include_fields", "close,volume"
        ]
        subprocess.run(dump_cmd, check=True)

        print("Crypto data download/normalize/dump finished")
    except Exception as e:
        print(f"Crypto data retrieval failed: {e}")
        print("Please ensure you have crypto data in the provider directory:", provider_uri)
        return

    # Initialize qlib
    qlib.init(provider_uri=provider_uri, region=REG_CN)

    try:
        # Get crypto k-line data
        instruments = D.list_instruments(
            {"market": "all"}, 
            start_time="2025-01-01", 
            end_time="2025-10-05", 
            freq="1h", 
            as_list=True
        )
    except ValueError as e:
        print(f"Failed to load instruments: {e}")
        print(f"Please ensure your data is properly formatted in: {provider_uri}")
        return

    if not instruments:
        print(f"No instruments found in {provider_uri} for the specified period")
        return

    universe = instruments[:5]  # limit to 5 for demo

    import pandas as pd

    end = pd.Timestamp("2025-10-05")
    start = pd.Timestamp("2025-01-01")

    price_feat = D.features(universe, ["$close"], start, end, freq="1h", disk_cache=1)
    # normalize price_feat to a Series of close prices indexed by (instrument, datetime)
    if isinstance(price_feat, pd.DataFrame) and "$close" in price_feat.columns:
        s = price_feat["$close"]
    elif isinstance(price_feat, pd.Series):
        s = price_feat
    else:
        # try to extract first column
        s = price_feat.iloc[:, 0]

    price_wide = s.unstack(level=0)
    # next-period return as the signal (oracle-like for testing)
    ret = price_wide.pct_change().shift(-1)
    pred_series = ret.stack()
    # make sure index is (instrument, datetime)
    try:
        pred_series = pred_series.swap_level(0, 1).sort_index()
    except Exception:
        pred_series = pred_series.sort_index()

    # prepare port_analysis_config using CryptoTopNStrategy with the precomputed signal
    port_analysis_config = {
        "executor": {"class": "SimulatorExecutor", "module_path": "qlib.backtest.executor", "kwargs": {"time_per_step": "60min", "generate_portfolio_metrics": True}},
        "strategy": {
            "class": "CryptoTopNStrategy",
            "module_path": "qlib.contrib.strategy.crypto_strategy",
            "kwargs": {
                "signal": pred_series,
                "universe": universe,
                "top_n": 3,
                "max_leverage": 3.0,
                "sizing": "equal_dollar",
                "vol_lookback": 20,
                "only_tradable": True,
            },
        },
        "backtest": {"start_time": str(pred_series.index.get_level_values(1).min()), "end_time": str(pred_series.index.get_level_values(1).max()), "account": 100000, "benchmark": None, "exchange_kwargs": {"freq": "1h", "limit_threshold": 0.095, "deal_price": "close", "open_cost": 0.0005, "close_cost": 0.0005, "min_cost": 1}},
    }

    # prepare dataset for train
    from qlib.data.dataset import DatasetH
    from qlib.data.dataset.handler import Alpha158

    dataset_config = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": {
                "class": "Alpha158",
                "module_path": "qlib.data.dataset.handler",
                "kwargs": {
                    "start_time": start,
                    "end_time": end,
                    "fit_start_time": start,
                    "fit_end_time": end,
                    "instruments": universe,
                    "freq": "1h",
                    "infer_processors": [],
                    "learn_processors": [],
                    "shared_processors": [],
                    "process_type": "independent",
                },
            },
            "segments": {
                "train": (start, end),
                "valid": (start, end),
                "test": (start, end),
            },
        },
    }

    dataset = init_instance_by_config(dataset_config)

    # start workflow train and save model
    from qlib.utils import init_instance_by_config
    from qlib.workflow.record_temp import SignalRecord, PortAnaRecord, SigAnaRecord

    model_config = {
        "class": "LGBModel",
        "module_path": "qlib.contrib.model.gbdt",
        "kwargs": {
            "loss": "mse",
            "colsample_bytree": 0.8879,
            "learning_rate": 0.0421,
            "subsample": 0.8789,
            "lambda_l1": 205.6999,
            "lambda_l2": 580.9768,
            "max_depth": 8,
            "num_leaves": 210,
            "num_threads": 20,
        },
    }

    model = init_instance_by_config(model_config)

    with R.start(experiment_name="crypto_intraday_demo"):
        R.log_params(strategy=str(port_analysis_config["strategy"]["class"]))

        # prepare dataset for train
        example_df = dataset.prepare("train")
        print(example_df.head())

        # start workflow train and save model
        model.fit(dataset)
        R.save_objects(**{"params.pkl": model})

        # prediction
        recorder = R.get_recorder()
        sr = SignalRecord(model, dataset, recorder)
        sr.generate()

        # Signal Analysis
        sar = SigAnaRecord(recorder)
        sar.generate()

        # backtest with CryptoTopNStrategy
        par = PortAnaRecord(recorder, port_analysis_config, "60min")
        par.generate()

        # report backtesting performance
        print("Backtest completed. Check the recorder for performance metrics.")


if __name__ == "__main__":
    main()
