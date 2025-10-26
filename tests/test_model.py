import pytest
import pandas as pd
import numpy as np
from qlib.model.crypto import LGBTrainer

def test_model_training():
    """Test LightGBM model training wrapper"""
    # Generate synthetic training data
    np.random.seed(42)
    n_samples = 1000
    X = pd.DataFrame({
        f"feature_{i}": np.random.randn(n_samples) 
        for i in range(10)
    })
    y = (X["feature_0"] + X["feature_1"] > 0).astype(int)
    
    trainer = LGBTrainer()
    model = trainer.train(X, y)
    
    # Verify model properties
    assert model is not None
    assert hasattr(model, "predict")
    
    # Test prediction shape
    preds = model.predict(X)
    assert len(preds) == len(X)
    assert all((preds >= 0) & (preds <= 1))

def test_model_validation():
    """Test model validation and metrics"""
    trainer = LGBTrainer()
    
    # Train with validation set
    X = pd.DataFrame(np.random.randn(1000, 10))
    y = (X[0] + X[1] > 0).astype(int)
    
    metrics = trainer.train_validate(
        X_train=X[:800], 
        y_train=y[:800],
        X_val=X[800:], 
        y_val=y[800:]
    )
    
    assert "accuracy" in metrics
    assert "sharpe" in metrics
    assert metrics["accuracy"] > 0.5  # Better than random
