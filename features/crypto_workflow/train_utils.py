import lightgbm as lgb
import numpy as np
from sklearn.metrics import roc_auc_score, mean_squared_error
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LGBModel:
    """LightGBM model wrapper with simplified training interface."""
    
    DEFAULT_PARAMS = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9
    }

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        self.model = None
        
    def fit(self, X, y, eval_set=None, early_stopping_rounds=100):
        """Train model with early stopping."""
        train_data = lgb.Dataset(X, label=y)
        valid_data = None if eval_set is None else lgb.Dataset(*eval_set)

        callbacks = [lgb.log_evaluation(period=100)]
        if valid_data is not None:
            callbacks.append(lgb.early_stopping(early_stopping_rounds))

        self.model = lgb.train(
            self.params,
            train_data,
            valid_sets=[valid_data] if valid_data else None,
            callbacks=callbacks
        )
        
        # Compute training metrics
        y_pred = self.predict(X)
        metrics = {}
        if self.params['objective'] == 'binary':
            metrics['train_auc'] = roc_auc_score(y, y_pred)
        else:
            metrics['train_rmse'] = np.sqrt(mean_squared_error(y, y_pred))
            
        return metrics
    
    def predict(self, X):
        """Generate predictions."""
        if self.model is None:
            raise RuntimeError("Model not trained. Call fit() first.")
        return self.model.predict(X)
        
    def save(self, path: str):
        """Save model to file."""
        if self.model is None:
            raise RuntimeError("No model to save. Train first.")
        self.model.save_model(path)
        
    def load(self, path: str):
        """Load model from file."""
        self.model = lgb.Booster(model_file=path)
