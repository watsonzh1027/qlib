import sys
from pathlib import Path
import json
import pandas as pd
import pickle
import qlib
from qlib.data import D
from qlib.config import REG_CN
from qlib.utils import init_instance_by_config
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, PortAnaRecord

# Add paths
CUR_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import our custom modules
from scripts.train_multiscale import MultiScaleTrainer
from qlib.contrib.strategy.multiscale_strategy import dynamic_ensemble

def load_model(timeframe):
    model_path = Path("models/multiscale") / f"model_{timeframe}.bin"
    if not model_path.exists():
        raise FileNotFoundError(f"Model for {timeframe} not found at {model_path}")
    with open(model_path, "rb") as f:
        return pickle.load(f)

def get_dataset(timeframe, trainer_config):
    # Reconstruct dataset config from trainer config
    tf_config = trainer_config["timeframes"][timeframe]
    dh_config = trainer_config["data_handler_config"].copy()
    dh_config["freq"] = tf_config["freq"]
    dh_config["instruments"] = ["ETH_USDT"]
    dh_config["label"] = tf_config["label"] # Important for dataset init, though we only predict
    
    # We want to predict on the BACKTEST period (e.g. 2024-2025)
    # Actually let's use the 'test' segment from config
    # test: 2025-01-01 to 2025-12-31 usually
    
    dataset_config = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": {
                "class": "Alpha158",
                "module_path": "qlib.contrib.data.handler",
                "kwargs": dh_config
            },
            "segments": {
                "test": ("2024-01-01", "2025-12-31"), # 2 Year Backtest coverage
            }
        }
    }
    return init_instance_by_config(dataset_config)

def run_multiscale_backtest():
    # 1. Setup
    with open("config/workflow_multiscale.json", "r") as f:
        config = json.load(f)

    # 2. Generate Predictions
    preds = {}
    for tf in ["240min", "60min", "15min"]:
        print(f"Generating predictions for {tf}...")
        provider_uri = f"data/qlib_data/crypto_{tf}"
        if not Path(provider_uri).exists():
             print(f"Data directory {provider_uri} not found. Skipping.")
             continue
             
        qlib.init(provider_uri=provider_uri, region=REG_CN)
        
        try:
            model = load_model(tf)
            dataset = get_dataset(tf, config)
            pred = model.predict(dataset, segment="test")
            
            # Helper to cleanup index
            if isinstance(pred, pd.DataFrame):
                pred = pred.iloc[:, 0]
                
            # Ensure multiindex (datetime, instrument)
            # Qlib prediction result index is usually (datetime, instrument)
            preds[tf] = pred
            
        except FileNotFoundError:
            print(f"Skipping {tf}: Model not found.")
        except Exception as e:
            print(f"Error predicting {tf}: {e}")

    if "240min" not in preds:
        print("Critical Error: Base 240min prediction missing!")
        return

    # 3. Alignment
    # Align everything to 240min index
    base_idx = preds["240min"].index
    
    # DataFrame to hold aligned scores
    df_aligned = pd.DataFrame(index=base_idx)
    df_aligned["240min"] = preds["240min"]
    
    # Align 60min
    # Logic: For a 4h bar at T, we want the prediction available at T.
    # The 60min prediction at T is valid.
    # So we just reindex?
    # Index is (datetime, instrument). Datetime is start_time usually in Qlib.
    # If 4h bar starts at 00:00, 60min bar starts at 00:00.
    # So direct index match works for the bars that align.
    
    for tf in ["60min", "15min"]:
        if tf in preds:
            # Reindex to base (keep only timestamps present in base)
            # Since data is higher freq, they should have the timestamps of base.
            df_aligned[tf] = preds[tf].reindex(base_idx)
    
    print("Alignment Stats:")
    print(df_aligned.count())
    
    # 4. Ensemble
    print("Calculating Ensemble Score...")
    # Default weights
    weights = {'240min': 0.5, '60min': 0.3, '15min': 0.2}
    combined_score = dynamic_ensemble(df_aligned, weights)
    
    # 5. Backtest
    print("Running Backtest with Combined Score...")
    
    # Create a simple generic strategy uses this score
    # We can use TopkDropoutStrategy or similar
    
    # Market & Benchmark
    market = "crypto"
    benchmark = "ETH_USDT" # Single asset backtest against itself basically
    
    # Executor Config
    executor_config = {
        "class": "SimulatorExecutor",
        "module_path": "qlib.backtest.executor",
        "kwargs": {
            "time_per_step": "240min",
            "generate_portfolio_metrics": True,
        }
    }
    
    # Strategy Config
    # Since we have pre-calculated score, we can use 'TopkDropoutStrategy'
    # But we need to pass the 'pred_score' to it?
    # Standard Qlib workflow allows passing 'pred_score' in `backtest` function.
    
    strategy_config = {
        "class": "RiskControlStrategy",
        "module_path": "risk_strategy",
        "kwargs": {
            "signal": combined_score,
            "buy_threshold": 0.001,  # Slight positive threshold
            "sell_threshold": -0.001,
            "stop_loss": 0.05,
            "take_profit": 0.15,
            "risk_degree": 0.95
        }
    }
    
    # Standard Qlib backtest run helper
    from qlib.backtest import backtest as run_backtest_func
    # But `backtest` func expects `pred_score` as pd.Series/DataFrame.
    
    # We passed `signal` in kwargs above is wrong for standard strategies usually. 
    # Standard strategies load signal from dataset or file.
    # But Qlib's `common_infra` lets us patch.
    
    # Actually simpler: Use `backtest(pred_score=combined_score, ...)`
    
    start_time = combined_score.index.get_level_values(0).min()
    end_time = combined_score.index.get_level_values(0).max()
    
    # Re-init Qlib for Backtest (Base Freq)
    qlib.init(provider_uri="data/qlib_data/crypto_240min", region=REG_CN)

    exchange_kwargs = {
        "freq": "240min",
        "limit_threshold": 0.05,
        "deal_price": "close",
        "open_cost": 0.0005,
        "close_cost": 0.0005,
        "min_cost": 0,
    }

    report_normal, positions_normal = run_backtest_func(
        start_time=start_time,
        end_time=end_time,
        strategy=strategy_config,
        executor=executor_config,
        benchmark=None,
        exchange_kwargs=exchange_kwargs,
    )
    
    print("\nBacktest Results:")
    import pprint
    # report_normal is portfolio_metric_dict
    pprint.pprint(report_normal)
    
    # Save results
    res_dir = Path("output/multiscale")
    res_dir.mkdir(parents=True, exist_ok=True)
    combined_score.to_csv(res_dir / "combined_score.csv")
    
    # Extract dataframe from dict
    # report_normal is portfolio_metric_dict: {freq: (report_df, positions_df)}
    if isinstance(report_normal, dict):
        for freq, result in report_normal.items():
            if isinstance(result, tuple):
                report_df, positions_df = result
                report_df.to_csv(res_dir / f"report_{freq}.csv")
                
                # Handle positions saving
                if isinstance(positions_df, dict):
                    # Convert positions dict to DataFrame for easier CSV viewing
                    # Structure: {timestamp: PositionOrDict}
                    # We want to extract key metrics or just dump it
                    try:
                        # Simple flat conversion: Index=Time, Columns=Assets
                        # Check first item to see structure
                        first_pos = next(iter(positions_df.values()))
                        if hasattr(first_pos, 'position'): # It's a Position object
                            pos_data = {k: v.position for k, v in positions_df.items()}
                        else:
                            pos_data = positions_df
                            
                        # This might be nested, so just normalize
                        positions_reform = pd.DataFrame.from_dict(pos_data, orient='index')
                        positions_reform.to_csv(res_dir / f"positions_{freq}.csv")
                    except Exception as e:
                        print(f"Failed to convert positions to CSV: {e}")
                        import pickle
                        with open(res_dir / f"positions_{freq}.pkl", "wb") as f:
                            pickle.dump(positions_df, f)
                        print(f"Saved positions as PKL instead.")
                elif isinstance(positions_df, pd.DataFrame):
                    positions_df.to_csv(res_dir / f"positions_{freq}.csv")
                
                print(f"Saved report and positions for {freq}")
                
                # Print Metrics
                try:
                    # 'account' contains the account value
                    latest_val = report_df['account'].iloc[-1]
                    total_ret = latest_val / 1e9 - 1
                    print(f"Final Account Value: {latest_val:,.2f}")
                    print(f"Cumulative Return: {total_ret:.2%}")
                except Exception as e:
                    print(f"Metric print failed: {e}")
                    print(f"Columns: {report_df.columns}")

    else:
        print(f"Unexpected report_normal type: {type(report_normal)}")
        
    print(f"Results saved to {res_dir}")

if __name__ == "__main__":
    run_multiscale_backtest()
