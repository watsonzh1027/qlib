import json
import pandas as pd
import numpy as np
from pathlib import Path
import yaml
from typing import Dict, Optional

class SignalGenerator:
    """Generate trading signals from model predictions"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """Load signal generation configuration"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "features/crypto-workflow/config_defaults.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)["trading"]
    
    def generate(self, predictions: pd.Series) -> pd.DataFrame:
        """Generate trading signals from model predictions"""
        signals = pd.DataFrame(index=predictions.index)
        signals["score"] = predictions
        
        # Generate signals based on thresholds
        conditions = [
            (predictions > self.config["thresholds"]["buy"]),
            (predictions < self.config["thresholds"]["sell"]),
        ]
        choices = ["BUY", "SELL"]
        signals["signal"] = np.select(conditions, choices, default="HOLD")
        
        # Calculate position sizes
        signals["position_size"] = self._calculate_position_size(predictions)
        
        return signals
    
    def _calculate_position_size(self, scores: pd.Series) -> pd.Series:
        """Calculate position size based on model confidence"""
        # Linear scaling from 0 (full sell) to 1 (full buy)
        position_size = scores
        
        # Apply position limits
        max_position = self.config["position"]["max_size"]
        min_position = self.config["position"]["min_size"]
        position_size = position_size.clip(min_position, max_position)
        
        return position_size
    
    def save_signals(self, signals: pd.DataFrame, path: Path) -> None:
        """Save signals to CSV with metadata"""
        signals.to_csv(path)
        
        # Save metadata
        meta = {
            "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "thresholds": self.config["thresholds"],
            "position_limits": self.config["position"]
        }
        meta_path = path.with_suffix(".json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
