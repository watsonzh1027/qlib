#!/usr/bin/env python3
"""
Analysis Script for Hyperparameter Tuning
Generates HTML reports and visualization from Optuna Database.
"""

import optuna
import optuna.visualization as vis
import argparse
import json
from pathlib import Path
import os
import sys

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

def load_config():
    with open("config/workflow.json", "r") as f:
        return json.load(f)

def get_storage_url(config):
    db_cfg = config.get("database", {})
    if not db_cfg.get("use_db", False):
        return None
    user = db_cfg.get("user", "crypto_user")
    password = db_cfg.get("password", "crypto")
    host = db_cfg.get("host", "localhost")
    port = db_cfg.get("port", 5432)
    dbname = db_cfg.get("database", "qlib_crypto")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def generate_report(symbol, stage="strategy"):
    config = load_config()
    storage_url = get_storage_url(config)
    
    if not storage_url:
        print("❌ Error: Database usage is disabled in config/workflow.json")
        return

    safe_symbol = symbol.replace("/", "_")
    study_name = f"tuning_{stage}_{safe_symbol}"
    
    print(f"Loading study '{study_name}' from {storage_url}...")
    try:
        study = optuna.load_study(study_name=study_name, storage=storage_url)
    except Exception as e:
        print(f"❌ Could not load study: {e}")
        return

    # Create reports directory
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    
    print(f"✅ Study loaded. Best Value ({'Sharpe' if stage=='strategy' else 'IC'}): {study.best_value:.4f}")
    
    # Generate Plots
    try:
        # Optimization History
        fig_hist = vis.plot_optimization_history(study)
        hist_html = str(report_dir / f"{stage}_{safe_symbol}_history.html")
        fig_hist.write_html(hist_html)
        print(f"   > Saved History Plot: {hist_html}")
        
        # Param Importance
        fig_imp = vis.plot_param_importances(study)
        imp_html = str(report_dir / f"{stage}_{safe_symbol}_importance.html")
        fig_imp.write_html(imp_html)
        print(f"   > Saved Importance Plot: {imp_html}")
        
        # Parallel Coordinate
        fig_par = vis.plot_parallel_coordinate(study)
        par_html = str(report_dir / f"{stage}_{safe_symbol}_parallel.html")
        fig_par.write_html(par_html)
        print(f"   > Saved Parallel Plot: {par_html}")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not generate some plots. Error: {e}")

    # Export Top Trials to CSV
    df = study.trials_dataframe()
    csv_path = report_dir / f"{stage}_{safe_symbol}_trials.csv"
    df.to_csv(csv_path, index=False)
    print(f"   > Saved Trials Data: {csv_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True, help="Symbol to analyze (e.g. ETHUSDT)")
    parser.add_argument("--stage", choices=["model", "strategy"], default="strategy", help="Tuning stage")
    args = parser.parse_args()
    
    generate_report(args.symbol, args.stage)

if __name__ == "__main__":
    main()
