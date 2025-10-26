# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
LGB Trainer for crypto models.
"""

import pandas as pd
import numpy as np

class LGBTrainer:
    """
    LightGBM-based trainer for crypto models.
    """

    def __init__(self):
        self.model = None

    def train(self, X, y):
        """
        Train the model.

        Args:
            X: Training features.
            y: Training labels.

        Returns:
            model: Trained model.
        """
        import lightgbm as lgb
        
        # Convert data to LightGBM format
        train_data = lgb.Dataset(X, label=y)
        
        # Define model parameters
        params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": 0
        }
        
        # Train the model
        self.model = lgb.train(params, train_data, num_boost_round=100)

        return self.model

    def train_validate(self, X_train, y_train, X_val, y_val):
        """
        Train and validate the model.

        Args:
            X_train: Training features.
            y_train: Training labels.
            X_val: Validation features.
            y_val: Validation labels.

        Returns:
            model: Trained model.
            metrics: Validation metrics.
        """
        import lightgbm as lgb
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        # Convert data to LightGBM format
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

        # Define model parameters
        params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": 0
        }

        # Train the model with validation
        model = lgb.train(
            params,
            train_data,
            num_boost_round=100,
            valid_sets=[val_data],
            valid_names=['val']
        )

        # Predict on validation set
        val_preds_proba = model.predict(X_val)
        val_preds = (val_preds_proba > 0.5).astype(int)

        # Calculate metrics
        accuracy = accuracy_score(y_val, val_preds)
        precision = precision_score(y_val, val_preds, zero_division=0)
        recall = recall_score(y_val, val_preds, zero_division=0)
        f1 = f1_score(y_val, val_preds, zero_division=0)

        # Placeholder for sharpe - would need actual returns data
        sharpe = 1.0

        metrics = {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "sharpe": sharpe
        }

        self.model = model
        return model, metrics

    def save(self, model_dir):
        """
        Save the trained model to disk.

        Args:
            model_dir: Directory to save the model.
        """
        import json
        import os

        if self.model is None:
            raise ValueError("No model trained")

        # Create directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)

        # Save the model
        model_path = os.path.join(model_dir, "model.txt")
        self.model.save_model(model_path)

        # Save metadata
        metadata = {
            "model_type": "lightgbm",
            "objective": "binary",
            "num_boost_round": 100
        }
        metadata_path = os.path.join(model_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

    def load(self, model_dir):
        """
        Load a trained model from disk.

        Args:
            model_dir: Directory containing the saved model.
        """
        import json
        import os

        model_path = os.path.join(model_dir, "model.txt")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        import lightgbm as lgb
        self.model = lgb.Booster(model_file=model_path)
