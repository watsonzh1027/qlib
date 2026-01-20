import json
import argparse
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Run training and backtest using best parameters from workflow.best.json")
    parser.add_argument("--symbol", default="ETHUSDT", help="Symbol to use (must exist in per_symbol_models)")
    parser.add_argument("--config", default="config/workflow.best.json", help="Path to best config file")
    parser.add_argument("--start", default="2024-01-01", help="Backtest start date")
    parser.add_argument("--end", default="2024-12-31", help="Backtest end date")
    parser.add_argument("--leverage", type=float, help="Override leverage (e.g. 1.0)")
    parser.add_argument("--threshold", type=float, help="Override signal threshold (e.g. 0.002)")
    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / args.config
    
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    # Load best config
    with open(config_path, 'r') as f:
        base_config = json.load(f)

    if args.symbol not in base_config.get("per_symbol_models", {}):
        print(f"Error: No best model found for {args.symbol} in {args.config}")
        print("Available symbols:", list(base_config.get("per_symbol_models", {}).keys()))
        sys.exit(1)

    print(f"Applying best parameters for {args.symbol}...")
    best_params = base_config["per_symbol_models"][args.symbol]
    model_type = best_params["model_type"]
    
    # 1. Update Strategy Params (Top Level)
    if "strategy" not in base_config:
        base_config["strategy"] = {}
    
    # Overwrite strategy params
    print(f"  -> Updating Strategy params: {best_params['trading']}")
    base_config["strategy"].update(best_params["trading"])
    
    # Allow Manual Override for Robustness Testing
    if args.leverage is not None:
        print(f"  ⚠️ Overriding Leverage: {args.leverage}")
        base_config["strategy"]["leverage"] = args.leverage
        
    if args.threshold is not None:
        print(f"  ⚠️ Overriding Threshold: {args.threshold}")
        base_config["strategy"]["signal_threshold"] = args.threshold
    
    # 2. Update Model Params
    if "training" in base_config and "models" in base_config["training"]:
        if model_type in base_config["training"]["models"]:
             print(f"  -> Updating Model ({model_type}) params")
             base_config["training"]["models"][model_type].update(best_params["model_params"])
        else:
             print(f"Warning: Model type {model_type} not found in training.models config.")
    
    # Ensure the active model type is set
    base_config["training"]["model_type"] = model_type
    
    # Inject instruments into training config (required by train_sample_model.py)
    if "instruments" not in base_config["training"]:
        base_config["training"]["instruments"] = []
    # Ensure it's a list
    base_config["training"]["instruments"] = [args.symbol]

    # 3. Save to temp config
    temp_config_name = f"workflow.run_best.{args.symbol}.json"
    temp_config_path = project_root / "config" / temp_config_name
    
    with open(temp_config_path, 'w') as f:
        json.dump(base_config, f, indent=4)
    
    print(f"Generated runtime config: {temp_config_path}")

    # 4. Train Model
    print("\n" + "="*50)
    print("🚀 STEP 1: Retraining Model with Best Parameters")
    print("="*50)
    
    # Define training period (Standard 2024 Backtest Setup)
    # Train: 2021-01-01 -> 2023-10-31
    # Valid: 2023-11-01 -> 2023-12-31
    train_start = "2021-01-01"
    train_end = "2023-10-31"
    valid_start = "2023-11-01"
    valid_end = "2023-12-31"

    cmd_train = [
        sys.executable, str(project_root / "scripts/train_sample_model.py"), 
        "--config", str(temp_config_path),
        "--train-start", train_start,
        "--train-end", train_end,
        "--valid-start", valid_start,
        "--valid-end", valid_end
    ]
    try:
        subprocess.check_call(cmd_train)
    except subprocess.CalledProcessError as e:
        print(f"Training failed with code {e.returncode}")
        sys.exit(e.returncode)

    # 5. Run Backtest
    print("\n" + "="*50)
    print("🚀 STEP 2: Running Final Backtest")
    print("="*50)
    
    cmd_backtest = [
        sys.executable, str(project_root / "scripts/run_backtest.py"), 
        "--config", str(temp_config_path),
        "--start", args.start,
        "--end", args.end
    ]
    try:
        subprocess.check_call(cmd_backtest)
    except subprocess.CalledProcessError as e:
        print(f"Backtest failed with code {e.returncode}")
        sys.exit(e.returncode)

    print("\n✅ Process Complete!")

if __name__ == "__main__":
    main()
