#!/usr/bin/env python3
"""
Two-Stage Hyperparameter Tuning Script for Qlib Crypto Platform
Phase 1: Optimize Model (IC/ICIR) - Fast
Phase 2: Optimize Strategy (Sharpe) - Slower but eliminates model training overhead
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
from qlib.utils.logging_config import startlog

# Configure logging
logger = startlog(name="tuning")

CONFIG_PATH = Path("config/workflow.json")
BACKUP_PATH = Path("config/workflow.json.bak")
BEST_CONFIG_PATH = Path("config/workflow.best.json")
TMP_DIR = Path("tmp/tuning")

def setup_dirs():
    TMP_DIR.mkdir(parents=True, exist_ok=True)

def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)

def save_config(config: Dict[str, Any], path: Path):
    with open(path, "w") as f:
        json.dump(config, f, indent=4)

def run_command(cmd, env_vars: Optional[Dict[str, str]] = None):
    start_time = time.time()
    current_env = os.environ.copy()
    if env_vars:
        current_env.update(env_vars)
    result = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=current_env
    )
    duration = time.time() - start_time
    return result, duration

# --- Parsing Helpers ---
def parse_ic(output):
    match = re.search(r"IC:\s*([-\d.]+)", output)
    if match:
        return float(match.group(1))
    return -999.0

def parse_metrics(output):
    metrics = {
        "sharpe": -999.0, "annual_return": 0.0, "max_drawdown": 1.0,
        "win_rate": 0.0, "total_trades": 0
    }
    sharpe = re.search(r"Sharpe Ratio:\s*([-\d.]+)", output)
    if sharpe: metrics["sharpe"] = float(sharpe.group(1))
    
    ret = re.search(r"Annualized Return:\s*([-\d.]+)%", output)
    if ret: metrics["annual_return"] = float(ret.group(1)) / 100.0
    
    mdd = re.search(r"Max Drawdown:\s*([-\d.]+)%", output)
    if mdd: metrics["max_drawdown"] = float(mdd.group(1)) / 100.0
    
    trades = re.search(r"Total Trades:\s*([0-9]+)", output)
    if trades: metrics["total_trades"] = int(trades.group(1))
    
    return metrics

# --- WFV Fold Generator ---
def generate_wfv_folds(start_date, end_date, n_folds=3, ratio=(6, 1, 2), step_months=3):
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
        
        if test_end > end: break
            
        folds.append({
            "train": [f_start.strftime("%Y-%m-%d"), train_end.strftime("%Y-%m-%d")],
            "valid": [valid_start.strftime("%Y-%m-%d"), valid_end.strftime("%Y-%m-%d")],
            "test": [test_start.strftime("%Y-%m-%d"), test_end.strftime("%Y-%m-%d")],
        })
    return folds

# --- Objectives ---

def objective_model(trial, model_type, folds, base_config, symbol):
    """Phase 1: Optimize Model for IC"""
    trial_id = trial.number
    safe_symbol = symbol.replace("/", "_")
    config_path = TMP_DIR / f"cfg_model_{safe_symbol}_{trial_id}.json"
    
    # 1. Suggest Model Params
    params = {}
    if model_type == "lightgbm":
        params["learning_rate"] = trial.suggest_float("learning_rate", 0.01, 0.2, log=True)
        params["num_leaves"] = trial.suggest_int("num_leaves", 16, 255)
        params["lambda_l2"] = trial.suggest_float("lambda_l2", 1e-4, 10.0, log=True)
        params["max_depth"] = trial.suggest_int("max_depth", 3, 12)
        params["num_threads"] = 4
    
    # 2. Update Config
    trial_config = base_config.copy()
    if "training" not in trial_config: trial_config["training"] = {}
    if "models" not in trial_config["training"]: trial_config["training"]["models"] = {}
    if model_type not in trial_config["training"]["models"]: trial_config["training"]["models"][model_type] = {}
    
    trial_config["training"]["models"][model_type].update(params)
    trial_config["training"]["model_type"] = model_type
    trial_config["training"]["instruments"] = [symbol]
    
    save_config(trial_config, config_path)
    
    fold_ics = []
    
    for i, fold in enumerate(folds):
        # Train and validate (No Backtest)
        cmd = (f"{sys.executable} scripts/train_sample_model.py --config {config_path} "
               f"--model {model_type} "
               f"--train-start {fold['train'][0]} --train-end {fold['train'][1]} "
               f"--valid-start {fold['valid'][0]} --valid-end {fold['valid'][1]}")
        
        res, _ = run_command(cmd)
        ic = parse_ic(res.stdout)
        
        if ic == -999.0:
            logger.error(f"❌ Fold {i}: Tuning failed. Output snippet:\n{res.stdout[-300:]}")
            return -999.0
            
        fold_ics.append(ic)
        logger.info(f"   > Fold {i} IC: {ic:.4f}")

    # Cleanup
    if config_path.exists(): config_path.unlink()
    
    # Return Median IC
    return float(pd.Series(fold_ics).median())

def objective_strategy(trial, folds, base_config, symbol, best_model_params, model_type, pretrained_models):
    """Phase 2: Optimize Strategy for Sharpe (Using Fixed Model)"""
    trial_id = trial.number
    safe_symbol = symbol.replace("/", "_")
    config_path = TMP_DIR / f"cfg_strat_{safe_symbol}_{trial_id}.json"
    
    # 1. Suggest Strategy Params
    leverage = trial.suggest_int("leverage", 1, 3)
    threshold = trial.suggest_float("threshold", 1e-4, 0.05, log=True)
    stop_loss = -trial.suggest_float("stop_loss_abs", 0.01, 0.15)
    take_profit = trial.suggest_float("take_profit_abs", 0.02, 0.30)
    min_sigma = trial.suggest_float("min_sigma", 0.0, 1.0)
    
    # 2. Update Config
    trial_config = base_config.copy()
    
    # Inject Fixed Model Params (Just for consistency, though we use pretrained pickles)
    if "training" not in trial_config: trial_config["training"] = {}
    if "models" not in trial_config["training"]: trial_config["training"]["models"] = {}
    if model_type not in trial_config["training"]["models"]: trial_config["training"]["models"][model_type] = {}
    trial_config["training"]["models"][model_type].update(best_model_params)
    trial_config["training"]["instruments"] = [symbol]
    
    # Inject Strategy Params
    if "strategy" not in trial_config: trial_config["strategy"] = {}
    trial_config["strategy"]["leverage"] = leverage
    trial_config["strategy"]["signal_threshold"] = threshold
    trial_config["strategy"]["stop_loss"] = stop_loss
    trial_config["strategy"]["take_profit"] = take_profit
    trial_config["strategy"]["min_sigma_threshold"] = min_sigma
    trial_config["strategy"]["topk"] = 1
    
    save_config(trial_config, config_path)
    
    fold_sharpes = []
    
    for i, fold in enumerate(folds):
        # COPY Pretrained Model to expected location
        # run_backtest looks for tmp/tuning/{config_stem}.pkl
        target_pkl = TMP_DIR / f"{config_path.stem}.pkl"
        shutil.copy(pretrained_models[i], target_pkl)
        
        # Run Backtest (Skip Training)
        cmd = (f"{sys.executable} scripts/run_backtest.py --config {config_path} "
               f"--start {fold['test'][0]} --end {fold['test'][1]}")
        
        res, _ = run_command(cmd)
        metrics = parse_metrics(res.stdout)
        
        # Cleanup pickle to save space
        if target_pkl.exists(): target_pkl.unlink()
        
        if metrics["total_trades"] == 0:
            fold_sharpes.append(-999.0) # Penalty for no trades
        else:
            fold_sharpes.append(metrics["sharpe"])
            
    if config_path.exists(): config_path.unlink()
    
    median_sharpe = float(pd.Series(fold_sharpes).median())
    logger.info(f"   > Trial {trial_id} Median Sharpe: {median_sharpe:.4f}")
    return median_sharpe

# --- Main Runners ---

def get_storage_url(config: Dict[str, Any]) -> str:
    db_cfg = config.get("database", {})
    if not db_cfg.get("use_db", False):
        return None
    user = db_cfg.get("user", "crypto_user")
    password = db_cfg.get("password", "crypto")
    host = db_cfg.get("host", "localhost")
    port = db_cfg.get("port", 5432)
    dbname = db_cfg.get("database", "qlib_crypto")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

# --- Main Runners ---

def run_model_tuning(args, base_config, symbol, folds, model_type):
    logger.info(f"🚀 [Phase 1] Tuning Model for {symbol} (Target: IC)")
    storage_url = get_storage_url(base_config)
    study_name = f"tuning_model_{symbol.replace('/','_')}"
    
    study = optuna.create_study(
        study_name=study_name, 
        storage=storage_url, 
        direction="maximize", 
        load_if_exists=True
    )

    # Hint for parallel execution
    if args.n_jobs > 1:
        logger.info(f"⚠️  Parallel mode (n_jobs={args.n_jobs}) enabled. Console logs from workers may be buffered.")
        logger.info(f"👉 Please run: tail -f logs/qlib-tuning-1.log to monitor realtime details.")

    study.optimize(lambda t: objective_model(t, model_type, folds, base_config, symbol), 
                   n_trials=args.trials, n_jobs=args.n_jobs, show_progress_bar=True)
    
    logger.info(f"✅ Best IC: {study.best_value:.4f}")
    logger.info(f"🏆 Best Model Params: {study.best_params}")
    return study.best_params

def run_strategy_tuning(args, base_config, symbol, folds, model_type, best_model_params):
    logger.info(f"🚀 [Phase 2] Tuning Strategy for {symbol} (Target: Sharpe)")
    
    # 1. Pre-train models for each fold using Best Params
    logger.info("⏳ Pre-training models for all folds (to speed up detailed tuning)...")
    pretrained_models = []
    
    pretrain_cfg_path = TMP_DIR / f"pretrain_{symbol.replace('/','_')}.json"
    pretrain_cfg = base_config.copy()
    if "training" not in pretrain_cfg: pretrain_cfg["training"] = {}
    if "models" not in pretrain_cfg["training"]: pretrain_cfg["training"]["models"] = {}
    if model_type not in pretrain_cfg["training"]["models"]: pretrain_cfg["training"]["models"][model_type] = {}
    pretrain_cfg["training"]["models"][model_type].update(best_model_params)
    pretrain_cfg["training"]["instruments"] = [symbol]
    save_config(pretrain_cfg, pretrain_cfg_path)
    
    for i, fold in enumerate(folds):
        print(f"   > Pre-training Fold {i}...", end="", flush=True)
        # Train
        cmd = (f"{sys.executable} scripts/train_sample_model.py --config {pretrain_cfg_path} "
               f"--model {model_type} "
               f"--train-start {fold['train'][0]} --train-end {fold['train'][1]} "
               f"--valid-start {fold['valid'][0]} --valid-end {fold['valid'][1]}")
        res, _ = run_command(cmd)
        
        # The script saves to tmp/tuning/{config_stem}.pkl
        generated_pkl = TMP_DIR / f"{pretrain_cfg_path.stem}.pkl"
        
        if not generated_pkl.exists():
            logger.error(f"Failed to pre-train model for fold {i}. Log:\n{res.stdout[-500:]}")
            return None
            
        # Rename/Move to safe place
        saved_pkl = TMP_DIR / f"pretrained_{symbol.replace('/','_')}_fold{i}.pkl"
        shutil.move(generated_pkl, saved_pkl)
        pretrained_models.append(saved_pkl)
        print("Done.")
        
    # 2. Optimize Strategy
    storage_url = get_storage_url(base_config)
    study_name = f"tuning_strategy_{symbol.replace('/','_')}"
    
    study = optuna.create_study(
        study_name=study_name, 
        storage=storage_url, 
        direction="maximize", 
        load_if_exists=True
    )
    study.optimize(lambda t: objective_strategy(t, folds, base_config, symbol, 
                                                best_model_params, model_type, pretrained_models), 
                   n_trials=args.trials, n_jobs=args.n_jobs, show_progress_bar=True)
                   
    # 3. Cleanup Pretrained Models
    for p in pretrained_models:
        if p.exists(): p.unlink()
        
    logger.info(f"✅ Best Sharpe: {study.best_value:.4f}")
    logger.info(f"🏆 Best Strategy Params: {study.best_params}")
    return study.best_params

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["model", "strategy", "all"], default="all")
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--rows", type=int, default=None, help="Limit symbols")
    parser.add_argument("--model", default="lightgbm")
    parser.add_argument("--n_jobs", type=int, default=1, help="Parallel workers")
    args = parser.parse_args()
    
    setup_dirs()
    base_config = load_config()
    
    # Get symbols
    sym_cfg = base_config.get("data", {}).get("symbols", [])
    if isinstance(sym_cfg, str) and sym_cfg.endswith(".json"):
        with open(sym_cfg, "r") as f:
            symbols = json.load(f).get("symbols", [])
    else:
        symbols = sym_cfg
        
    if args.rows:
        symbols = symbols[:args.rows]
        
    logger.info(f"Target Symbols: {symbols}")
    
    # Generate Folds
    folds = generate_wfv_folds(
        start_date="2022-01-01", 
        end_date="2024-12-31", 
        n_folds=3
    )
    
    final_results = {}
    
    for symbol in symbols:
        logger.info(f"\n{'='*50}\nProcessing {symbol}\n{'='*50}")
        
        best_model_params = {}
        best_strat_params = {}
        
        # PHASE 1: MODEL
        if args.stage in ["model", "all"]:
            best_model_params = run_model_tuning(args, base_config, symbol, folds, args.model)
        else:
            # Fallback for strategy-only run (dummy defaults or load from config)
            # ideally read from existing config
            best_model_params = {"learning_rate": 0.05, "num_leaves": 31, "max_depth": 6} 
            
        # PHASE 2: STRATEGY
        if args.stage in ["strategy", "all"]:
            if not best_model_params:
                logger.warning("Skipping strategy tuning due to missing model params")
                continue
            best_strat_params = run_strategy_tuning(args, base_config, symbol, folds, args.model, best_model_params)
            
        # Save results (partial)
        if args.stage == "all":
            final_results[symbol] = {
                "model": best_model_params,
                "strategy": best_strat_params
            }
            
            # Update BEST config
            best_config = load_config(BACKUP_PATH) if BACKUP_PATH.exists() else load_config()
            if "per_symbol_models" not in best_config: best_config["per_symbol_models"] = {}
            
            best_config["per_symbol_models"][symbol] = {
                "model_type": args.model,
                "model_params": best_model_params,
                "trading": {
                    "leverage": best_strat_params.get("leverage", 1),
                    "signal_threshold": best_strat_params.get("threshold", 0.0),
                    "stop_loss": -best_strat_params.get("stop_loss_abs", 0.05),
                    "take_profit": best_strat_params.get("take_profit_abs", 0.1),
                    "min_sigma_threshold": best_strat_params.get("min_sigma", 0.0)
                },
                "backtest_topk": 1
            }
            save_config(best_config, BEST_CONFIG_PATH)

    logger.info("\n" + "="*80)
    logger.info("🎉 Optimization Complete!")
    logger.info("="*80)
    logger.info("To view detailed visualizations and reports, run:")
    
    for symbol in symbols:
        logger.info(f"\n[Symbol: {symbol}]")
        logger.info(f"  1. Model Analysis (IC/ICIR):")
        logger.info(f"     python scripts/analyze_tuning.py --symbol {symbol} --stage model")
        logger.info(f"  2. Strategy Analysis (Sharpe/Drawdown):")
        logger.info(f"     python scripts/analyze_tuning.py --symbol {symbol} --stage strategy")
        
    logger.info("\nReports will be saved to the 'reports/' directory.")
    logger.info("="*80 + "\n")

if __name__ == "__main__":
    main()
