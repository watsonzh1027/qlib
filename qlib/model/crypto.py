import lightgbm as lgb
import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, Tuple, Any

class LGBTrainer:
    """LightGBM model trainer with crypto-specific configurations"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.model = None
        self.feature_names = None
    
    def _load_config(self, config_path: str = None) -> Dict:
        """Load model configuration"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "features/crypto-workflow/config_defaults.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)["model"]
    
    def train(self, X: pd.DataFrame, y: pd.Series) -> lgb.Booster:
        """Train LightGBM model"""
        self.feature_names = X.columns.tolist()
        train_data = lgb.Dataset(X, label=y)
        
        params = self.config["params"]
        self.model = lgb.train(
            params=params,
            train_set=train_data,
            valid_sets=[train_data]
        )
        return self.model
    
    def train_validate(
        self, 
        X_train: pd.DataFrame, 
        y_train: pd.Series,
        X_val: pd.DataFrame, 
        y_val: pd.Series
    ) -> Tuple[lgb.Booster, Dict[str, float]]:
        """Train with validation data and return metrics"""
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val)
        
        self.model = lgb.train(
            params=self.config["params"],
            train_set=train_data,
            valid_sets=[train_data, val_data],
            valid_names=["train", "valid"]
        )
        
        # Calculate metrics
        val_pred = self.model.predict(X_val)
        metrics = self._calculate_metrics(y_val, val_pred)
        
        return self.model, metrics
    
    def _calculate_metrics(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate model performance metrics"""
        threshold = 0.5
        pred_labels = (y_pred > threshold).astype(int)
        
        metrics = {
            "accuracy": (pred_labels == y_true).mean(),
            "precision": precision_score(y_true, pred_labels),
            "recall": recall_score(y_true, pred_labels),
            "f1": f1_score(y_true, pred_labels)
        }
        return metrics
    
    def save(self, path: Path) -> None:
        """Save model and metadata"""
        if self.model is None:
            raise ValueError("No model trained yet")
            
        # Save model
        model_path = path / "model.txt"
        self.model.save_model(str(model_path))
        
        # Save metadata
        meta = {
            "feature_names": self.feature_names,
            "params": self.config["params"],
            "version": self.config["version"]
        }
        with open(path / "metadata.json", "w") as f:
            json.dump(meta, f, indent=2)
    
    def load(self, path: Path) -> None:
        """Load model and metadata"""
        model_path = path / "model.txt"
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
            
        self.model = lgb.Booster(model_file=str(model_path))
        
        # Load metadata
        with open(path / "metadata.json") as f:
            meta = json.load(f)
        self.feature_names = meta["feature_names"]
