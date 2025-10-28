#!/usr/bin/env python3
"""
LightGBM model training script for crypto trading
"""
import sys
from pathlib import Path
import logging
import argparse
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

# Add qlib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from features.crypto_workflow.train_utils import LGBModel
from features.crypto_workflow.model_io import save_model
from qlib.utils.io import write_parquet

logger = logging.getLogger(__name__)

def train_model(feature_path: Path, model_path: Path) -> None:
    """Train LightGBM model on preprocessed features"""
    raise NotImplementedError("This function is not implemented yet.")

def train_from_features(
    features_path: str,
    model_dir: str,
    model_name: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    early_stopping_rounds: int = 50,
):
    """Load features parquet, build simple target, train LightGBM and save model + report."""
    features_path = Path(features_path)
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(str(features_path))
    # Expect returns column; build binary target: next-period positive return
    if 'returns' not in df.columns:
        raise ValueError("Features must contain 'returns' column to build target.")

    target = df['returns'].shift(-1)
    # Align X and y
    df = df.iloc[:-1].copy()
    y = (target.iloc[:-1] > 0).astype(int)

    # Drop non-numeric columns (symbol, timeframe)
    X = df.select_dtypes(include=[np.number]).copy()
    # Drop any columns that are entirely NaN
    X = X.dropna(axis=1, how='all')

    # Drop rows with NaNs
    valid_idx = X.dropna().index.intersection(y.dropna().index)
    X = X.loc[valid_idx]
    y = y.loc[valid_idx]

    if len(X) < 10:
        raise ValueError("Not enough data to train (need >=10 rows).")

    # Time-based split
    n = len(X)
    i1 = int(n * 0.7)
    i2 = int(n * 0.85)

    X_train, X_val, X_test = X.iloc[:i1], X.iloc[i1:i2], X.iloc[i2:]
    y_train, y_val, y_test = y.iloc[:i1], y.iloc[i1:i2], y.iloc[i2:]

    model = LGBModel(params=params)
    metrics = model.fit(
        X_train.values,
        y_train.values,
        eval_set=(X_val.values, y_val.values),
        early_stopping_rounds=early_stopping_rounds,
    )

    # Persist model via model_io.save_model (atomic)
    model_name = model_name or f"lgb_model_{features_path.stem}"
    model_path = model_dir / f"{model_name}.joblib"
    metadata = {
        "model_name": model_name,
        "params": model.params,
        "metrics": metrics,
        "symbol": None,
        "timeframe": None,
    }
    save_model(model, str(model_path), metadata=metadata)

    # Save simple training report
    report = {
        "model_path": str(model_path),
        "metrics": metrics,
        "train_rows": len(X_train),
        "val_rows": len(X_val),
        "test_rows": len(X_test),
    }
    report_path = model_dir / f"{model_name}_train_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Trained model saved to {model_path}")
    logger.info(f"Training report saved to {report_path}")
    return {"model_path": str(model_path), "report_path": str(report_path), "metrics": metrics}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--features-path", required=True, help="Path to features parquet")
    parser.add_argument("--model-dir", required=True, help="Directory to save model")
    parser.add_argument("--model-name", default=None, help="Optional model name")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    train_from_features(args.features_path, args.model_dir, args.model_name)

if __name__ == "__main__":
    main()
