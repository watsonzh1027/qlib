#!/usr/bin/env python3
"""
Hyperparameter Tuning Script for Qlib Crypto Platform (Optuna Edition)
Uses Bayesian Optimization to find optimal parameters.
Supports parallel execution, PostgreSQL persistence, and resource optimization.
Includes tuning for Model, Strategy, and Risk Control (SL/TP) parameters.
"""

import json
import subprocess
import re
import shutil
import time
import os
import optuna
import pandas as pd
from pathlib import Path
import logging
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import sys
from qlib.utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(name="model_tuning")

CONFIG_PATH = Path("config/workflow.json")
BACKUP_PATH = Path("config/workflow.json.bak")
BEST_CONFIG_PATH = Path("config/workflow.best.json")
HISTORY_PATH = Path("tuning_history.csv")
TMP_DIR = Path("tmp/tuning")

def setup_dirs():
    """Ensure temporary directories exist."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)

def generate_wfv_folds(start_date="2023-01-01", end_date="2025-01-01", n_folds=3, ratio=(6, 1, 2), step_months=3):
    """Generate folds for Walk-Forward Validation using custom ratios."""
    from datetime import timedelta
    from dateutil.relativedelta import relativedelta
    
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    unit_days = 30
    folds = []
    
    for i in range(n_folds):
        f_start = start + relativedelta(months=i * step_months)
        
        d_train = ratio[0] * unit_days
        d_valid = ratio[1] * unit_days
        d_test = ratio[2] * unit_days
        
        train_end = f_start + timedelta(days=d_train)
        valid_start = train_end + timedelta(days=1)
        valid_end = valid_start + timedelta(days=d_valid)
        test_start = valid_end + timedelta(days=1)
        test_end = test_start + timedelta(days=d_test)
        
        if test_end > end:
            if test_start < end:
                test_end = end
            else:
                break
            
        folds.append({
            "train": [f_start.strftime("%Y-%m-%d"), train_end.strftime("%Y-%m-%d")],
            "valid": [valid_start.strftime("%Y-%m-%d"), valid_end.strftime("%Y-%m-%d")],
            "test": [test_start.strftime("%Y-%m-%d"), test_end.strftime("%Y-%m-%d")],
        })
    return folds

def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)

def save_config(config: Dict[str, Any], path: Path = CONFIG_PATH):
    with open(path, "w") as f:
        json.dump(config, f, indent=4)

def run_command(cmd, env_vars: Optional[Dict[str, str]] = None):
    """Run a shell command and return the result."""
    start_time = time.time()
    
    current_env = os.environ.copy()
    if env_vars:
        current_env.update(env_vars)
        
    result = subprocess.run(
        cmd, 
        shell=True, 
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=current_env
    )
    duration = time.time() - start_time
    return result, duration

def parse_metrics(output):
    """Extract metrics from backtest output."""
    metrics = {
        "sharpe": -999.0,
        "annual_return": 0.0,
        "max_drawdown": 1.0,
        "sortino": -999.0,
        "calmar": -999.0,
        "win_rate": 0.0
    }
    
    sharpe_match = re.search(r"Sharpe Ratio:\s*([-\d.]+)", output)
    if not sharpe_match:
        sharpe_match = re.search(r"Sharpe=([-\d.]+)", output)
    if sharpe_match:
        metrics["sharpe"] = float(sharpe_match.group(1))
        
    return_match = re.search(r"Annualized Return:\s*([-\d.]+)%", output)
    if return_match:
        metrics["annual_return"] = float(return_match.group(1)) / 100.0
        
    mdd_match = re.search(r"Max Drawdown:\s*([-\d.]+)%", output)
    if mdd_match:
        metrics["max_drawdown"] = float(mdd_match.group(1)) / 100.0

    sortino_match = re.search(r"Sortino Ratio:\s*([-\d.]+)", output)
    if sortino_match:
        metrics["sortino"] = float(sortino_match.group(1))

    calmar_match = re.search(r"Calmar Ratio:\s*([-\d.]+)", output)
    if calmar_match:
        metrics["calmar"] = float(calmar_match.group(1))

    win_match = re.search(r"Win Rate:\s*([-\d.]+)%", output)
    if win_match:
        metrics["win_rate"] = float(win_match.group(1)) / 100.0
    # Total trades (if present)
    trades_match = re.search(r"Total Trades:\s*([0-9]+)", output)
    if trades_match:
        metrics["total_trades"] = int(trades_match.group(1))
    else:
        metrics["total_trades"] = 0
        
    return metrics

def calculate_composite_score(metrics):
    """Calculate Weighted Performance Score (WPS)"""
    sharpe_score = max(0, metrics["sharpe"]) * 0.40
    sortino_score = max(0, metrics["sortino"]) * 0.15
    calmar_score = max(0, metrics["calmar"]) * 0.10
    win_rate_score = (metrics["win_rate"] / 0.5) * 0.10
    
    composite = sharpe_score + sortino_score + calmar_score + win_rate_score
    
    mdd = metrics["max_drawdown"]
    if mdd > 0.50:
        return -999.0
    
    penalty = 0.0
    if mdd > 0.20:
        penalty = (mdd - 0.20) * 2.0
        
    return composite - penalty

def objective(trial, model_type, folds, base_config, symbol):
    """Optuna objective function for a specific symbol."""
    trial_id = trial.number
    # Sanitize symbol for filename
    safe_symbol = symbol.replace("/", "_")
    trial_config_path = TMP_DIR / f"config_{model_type}_{safe_symbol}_{trial_id}.json"
    
    tuning_cfg = base_config.get("tuning", {})
    n_epochs = tuning_cfg.get("n_epochs", 20)
    early_stop = tuning_cfg.get("early_stop", 10)
    threads_per_job = str(tuning_cfg.get("max_threads_per_job", 2))
    hs_options = tuning_cfg.get("hidden_size_options", [32, 64])
    
    # 1. Model Parameters
    params = {}
    if model_type == "lightgbm":
        params["learning_rate"] = trial.suggest_float("learning_rate", 0.005, 0.1, log=True)
        params["num_leaves"] = trial.suggest_int("num_leaves", 7, 127)
        params["lambda_l2"] = trial.suggest_float("lambda_l2", 1e-4, 10.0, log=True)
        params["max_depth"] = trial.suggest_int("max_depth", 3, 15)
        params["num_threads"] = int(threads_per_job)
    elif model_type == "xgboost":
        params["learning_rate"] = trial.suggest_float("learning_rate", 0.005, 0.1, log=True)
        params["max_depth"] = trial.suggest_int("max_depth", 3, 12)
        params["n_estimators"] = trial.suggest_int("n_estimators", 100, 1000)
        params["nthread"] = int(threads_per_job)
    elif model_type in ["lstm", "alstm"]:
        params["lr"] = trial.suggest_float("lr", 1e-5, 5e-3, log=True)
        params["dropout"] = trial.suggest_float("dropout", 0.1, 0.6)
        params["hidden_size"] = trial.suggest_categorical("hidden_size", hs_options)
        params["n_epochs"] = n_epochs
        params["early_stop"] = early_stop
        if model_type == "alstm":
            params["rnn_type"] = trial.suggest_categorical("rnn_type", ["GRU", "LSTM"])
    
    # 2. Strategy Parameters
    strat_params = {}
    strat_params["topk"] = 1 # Single crypto, no topk selection needed
    strat_params["leverage"] = trial.suggest_int("leverage", 1, 3)
    strat_params["threshold"] = trial.suggest_float("threshold", 0.0, 0.001)
    
    # 3. Risk Control Parameters (SL/TP/Sigma)
    risk_params = {}
    # Stop Loss: Search from 0.01 (1%) to 0.10 (10%)
    risk_params["stop_loss"] = -trial.suggest_float("stop_loss_abs", 0.01, 0.15)
    # Take Profit: Search from 0.02 (2%) to 0.20 (20%)
    risk_params["take_profit"] = trial.suggest_float("take_profit_abs", 0.02, 0.30)
    # Min Sigma Threshold (Signal confidence)
    risk_params["min_sigma"] = trial.suggest_float("min_sigma", 0.0, 2.0)
    
    # Update config for this trial
    trial_config = base_config.copy()
    if "training" not in trial_config: trial_config["training"] = {}
    if "models" not in trial_config["training"]: trial_config["training"]["models"] = {}
    if model_type not in trial_config["training"]["models"]: trial_config["training"]["models"][model_type] = {}
    
    trial_config["training"]["models"][model_type].update(params)
    trial_config["training"]["model_type"] = model_type
    
    # INJECT PER-SYMBOL RESTRICTION
    trial_config["training"]["instruments"] = [symbol]
    
    if "backtest" not in trial_config: trial_config["backtest"] = {}
    if "trading" not in trial_config: trial_config["trading"] = {}
    trial_config["backtest"]["topk"] = strat_params["topk"]
    trial_config["trading"]["leverage"] = strat_params["leverage"]
    trial_config["trading"]["signal_threshold"] = strat_params["threshold"]
    trial_config["trading"]["stop_loss"] = risk_params["stop_loss"]
    trial_config["trading"]["take_profit"] = risk_params["take_profit"]
    trial_config["trading"]["min_sigma_threshold"] = risk_params["min_sigma"]

    # Also update 'strategy' section if it exists (for compatibility with run_backtest.py refactor)
    if "strategy" not in trial_config: 
        trial_config["strategy"] = {}
        
    # We update the strategy config with the tuned parameters
    # Note: CryptoLongShortStrategy uses flat kwargs in the JSON provided by user
    trial_config["strategy"]["leverage"] = strat_params["leverage"]
    trial_config["strategy"]["signal_threshold"] = strat_params["threshold"]
    trial_config["strategy"]["stop_loss"] = risk_params["stop_loss"]
    trial_config["strategy"]["take_profit"] = risk_params["take_profit"]
    trial_config["strategy"]["min_sigma_threshold"] = risk_params["min_sigma"]
    # Topk is usually in backtest or strategy, update both
    trial_config["strategy"]["topk"] = strat_params["topk"]
    
    save_config(trial_config, trial_config_path)
    
    env_vars = {
        "OMP_NUM_THREADS": threads_per_job,
        "MKL_NUM_THREADS": threads_per_job,
    }
    
    all_metrics = []
    composite_scores = []
    
    try:
        # Combine params for logging
        all_params = {**params, **strat_params, **risk_params}
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Trial {trial_id} ({symbol}) START | Params: {json.dumps(all_params)}", flush=True)

        for i, fold in enumerate(folds):
            # Check for embedding (Disabled for per-symbol usually, but optional)
            embedding_flag = ""
            if base_config.get("training", {}).get("use_embedding", False):
                embedding_flag = "--embedding"

            # Train
            print(f"[{datetime.now().strftime('%H:%M:%S')}]   > Fold {i+1}/{len(folds)} | ⏳ Training... ", end="", flush=True)
            train_cmd = (f"{sys.executable} scripts/train_sample_model.py --config {trial_config_path} "
                         f"--model {model_type} {embedding_flag} "
                         f"--train-start {fold['train'][0]} --train-end {fold['train'][1]} "
                         f"--valid-start {fold['valid'][0]} --valid-end {fold['valid'][1]}")
            train_res, _ = run_command(train_cmd, env_vars=env_vars)
            if train_res.returncode != 0:
                print(f"❌ Failed.\nSample Output: {train_res.stdout[:500]}", flush=True)
                composite_scores.append(-999.0)
                continue
            print("✅", flush=True)
                
            # Backtest
            print(f"[{datetime.now().strftime('%H:%M:%S')}]   > Fold {i+1}/{len(folds)} | 📈 Backtesting... ", end="", flush=True)
            bt_cmd = (f"{sys.executable} scripts/run_backtest.py --config {trial_config_path} "
                      f"--start {fold['test'][0]} --end {fold['test'][1]}")
            bt_res, _ = run_command(bt_cmd, env_vars=env_vars)
            if bt_res.returncode != 0:
                print(f"❌ Failed.\nSample Output: {bt_res.stdout[:500]}", flush=True)
                composite_scores.append(-999.0)
                continue
                
            metrics = parse_metrics(bt_res.stdout)
            # Penalize folds that produced zero trades (likely invalid/empty strategy)
            if metrics.get("total_trades", 0) == 0:
                score = -999.0
                print(f"⚠️ Fold {i+1}: zero trades detected — applying heavy penalty.", flush=True)
                
                # Extract Signal Stats
                sig_stats = re.search(r"DEBUG: Signal Stats.*", bt_res.stdout)
                thresh_info = re.search(r"DEBUG: Threshold:.*", bt_res.stdout)
                strat_weights = re.search(r"DEBUG: Strategy Generated Weights:.*", bt_res.stdout)
                if sig_stats:
                    print(f"   🔎 {sig_stats.group(0)}", flush=True)
                if thresh_info:
                    print(f"   🔎 {thresh_info.group(0)}", flush=True)
                if strat_weights:
                    print(f"   🔎 {strat_weights.group(0)}", flush=True)
                
                if not sig_stats and not thresh_info:
                    print("   🔎 Debug stats not found in output.", flush=True)
                
                # ALWAYS Print full output if zero trades to see Verbose Executor logs
                print(f"   🔎 Full Backtest Output:\n{bt_res.stdout}", flush=True)
            else:
                score = calculate_composite_score(metrics)
            all_metrics.append(metrics)
            composite_scores.append(score)
            print(f"✅ Score: {score:.3f} (Sharpe: {metrics['sharpe']:.2f})", flush=True)

        if not composite_scores:
            return -999.0

        # Use median aggregation across folds to be robust against outlier folds
        median_score = float(pd.Series(composite_scores).median())
        median_sharpe = float(pd.Series([m.get("sharpe", -999.0) for m in all_metrics]).median()) if all_metrics else -999.0

        trial.set_user_attr("sharpe_median", median_sharpe)
        trial.set_user_attr("max_drawdown", float(pd.Series([m.get("max_drawdown", 1.0) for m in all_metrics]).median()) if all_metrics else 1.0)

        return median_score
    finally:
        if trial_config_path.exists():
            trial_config_path.unlink()

def get_storage_url(config: Dict[str, Any]) -> Optional[str]:
    db_cfg = config.get("database", {})
    if not db_cfg.get("use_db", False):
        return None
    user = db_cfg.get("user", "crypto_user")
    password = db_cfg.get("password", "crypto")
    host = db_cfg.get("host", "localhost")
    port = db_cfg.get("port", 5432)
    dbname = db_cfg.get("database", "qlib_crypto") # Changed from dbname to database to match json
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def main():
    parser = argparse.ArgumentParser(description="Hyperparameter Tuning with Optuna (Per-Symbol)")
    parser.add_argument("--trials", type=int, default=20, help="Number of trials to run per symbol")
    parser.add_argument("--model", type=str, default=None, help="Model type to tune")
    parser.add_argument("--folds", type=int, default=3, help="Number of folds for WFV")
    parser.add_argument("--n_jobs", type=int, default=1, help="Parallel workers")
    parser.add_argument("--study_name", type=str, default=None, help="Base study name prefix")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated list of symbols to tune")
    args = parser.parse_args()

    setup_dirs()
    if not CONFIG_PATH.exists(): return

    shutil.copy(CONFIG_PATH, BACKUP_PATH)
    logger.info(f"Backed up config to {BACKUP_PATH}")

    try:
        base_config = load_config()
        model_type = args.model or base_config.get("training", {}).get("model_type", "lightgbm")
        
        # Determine symbols to tune
        if args.symbols:
            target_symbols = [s.strip() for s in args.symbols.split(",")]
        else:
            sym_cfg = base_config.get("data", {}).get("symbols", [])
            if isinstance(sym_cfg, str) and sym_cfg.endswith(".json"):
                with open(sym_cfg, "r") as f:
                    target_symbols = json.load(f).get("symbols", [])
            else:
                target_symbols = sym_cfg
            
        logger.info(f"Target Symbols: {target_symbols}")

        folds = generate_wfv_folds(
            start_date=base_config.get("training", {}).get("start_time", "2023-01-01"),
            # end_date=(datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d"),
            end_date=base_config.get("training", {}).get("end_time", "2025-12-31"),
            n_folds=args.folds,
            ratio=base_config.get("training", {}).get("rolling_window", {}).get("fold_ratio", [6,1,2]),
            step_months=base_config.get("training", {}).get("rolling_window", {}).get("step_months", 3)
        )
        
        storage_url = get_storage_url(base_config)
        base_study_name = args.study_name or f"crypto_tuning_{model_type}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        
        all_best_params = {}
        
        for symbol in target_symbols:
            safe_symbol = symbol.replace("/", "_")
            study_name = f"{base_study_name}_{safe_symbol}"
            
            logger.info(f"\n{'='*60}")
            logger.info(f"🚀 Starting Tuning for {symbol} (Study: {study_name})")
            logger.info(f"{'='*60}")
        
            study = optuna.create_study(study_name=study_name, storage=storage_url, direction="maximize", load_if_exists=True)
            study.optimize(lambda trial: objective(trial, model_type, folds, base_config, symbol), n_trials=args.trials, n_jobs=args.n_jobs)
            
            logger.info(f"✅ {symbol} Tuning Complete. Best WPS: {study.best_value:.4f}")
            logger.info(f"🏆 Best Params for {symbol}:\n{json.dumps(study.best_params, indent=2)}")
            all_best_params[symbol] = study.best_params

        # Update Config with Per-Symbol Params
        best_config = load_config(BACKUP_PATH)
        
        if "per_symbol_models" not in best_config:
            best_config["per_symbol_models"] = {}
        
        for symbol, best_params in all_best_params.items():
            # Process Params
            m_keys = ["learning_rate", "num_leaves", "lambda_l2", "max_depth", "n_estimators", "lr", "dropout", "hidden_size", "rnn_type"]
            model_updates = {k: v for k, v in best_params.items() if k in m_keys}
            
            # Construct per-symbol entry
            symbol_entry = {
                "model_type": model_type,
                "model_params": model_updates,
                "trading": {
                    "leverage": int(best_params.get("leverage", 1)),
                    "signal_threshold": best_params.get("threshold", 0.0),
                    "stop_loss": -best_params.get("stop_loss_abs", 0.1),
                    "take_profit": best_params.get("take_profit_abs", 0.2),
                    "min_sigma_threshold": best_params.get("min_sigma", 0.0)
                },
                "backtest_topk": int(best_params.get("topk", 3))
            }
            
            best_config["per_symbol_models"][symbol] = symbol_entry
            
        save_config(best_config, BEST_CONFIG_PATH)
        
        print("\n" + "="*80)
        print(f"🥇 PER-SYMBOL OPTIMIZATION COMPLETE")
        print(f"Results saved to {BEST_CONFIG_PATH} under 'per_symbol_models'")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        if BACKUP_PATH.exists(): shutil.copy(BACKUP_PATH, CONFIG_PATH)

if __name__ == "__main__":
    main()
