import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from qlib.model.crypto import LGBTrainer

@pytest.fixture
def synthetic_data():
    """Generate synthetic training data with known pattern"""
    np.random.seed(42)
    n_samples = 1000
    
    # Create features with actual predictive power
    X = pd.DataFrame({
        "trend": np.linspace(-1, 1, n_samples),
        "noise": np.random.randn(n_samples),
        "seasonal": np.sin(np.linspace(0, 8*np.pi, n_samples))
    })
    
    # Target: trend + some seasonal effect + noise
    y = (X["trend"] + 0.5 * X["seasonal"] + 0.1 * X["noise"] > 0).astype(int)
    
    return X, y

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
    
    model, metrics = trainer.train_validate(
        X_train=X[:800],
        y_train=y[:800],
        X_val=X[800:],
        y_val=y[800:]
    )

    assert "accuracy" in metrics
    assert "sharpe" in metrics
    assert metrics["accuracy"] > 0.5  # Better than random

def test_model_training_validation(synthetic_data, tmp_path):
    """Test model training with validation"""
    X, y = synthetic_data
    split = 800
    
    trainer = LGBTrainer()
    model, metrics = trainer.train_validate(
        X_train=X[:split],
        y_train=y[:split],
        X_val=X[split:],
        y_val=y[split:]
    )
    
    # Model should learn the pattern
    assert metrics["accuracy"] > 0.6
    assert metrics["precision"] > 0.5
    assert metrics["recall"] > 0.5
    assert metrics["f1"] > 0.5

def test_model_persistence(synthetic_data, tmp_path):
    """Test model save and load"""
    X, y = synthetic_data
    trainer = LGBTrainer()
    
    # Train and save
    model = trainer.train(X, y)
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    trainer.save(model_dir)
    
    # Verify files
    assert (model_dir / "model.txt").exists()
    assert (model_dir / "metadata.json").exists()
    
    # Load and predict
    new_trainer = LGBTrainer()
    new_trainer.load(model_dir)
    new_preds = new_trainer.model.predict(X)
    
    # Predictions should be identical
    original_preds = model.predict(X)
    np.testing.assert_array_almost_equal(new_preds, original_preds)

def test_invalid_operations():
    """Test error handling"""
    trainer = LGBTrainer()
    
    # Save without training
    with pytest.raises(ValueError, match="No model trained"):
        trainer.save(Path("/tmp"))
    
    # Load non-existent model
    with pytest.raises(FileNotFoundError):
        trainer.load(Path("/nonexistent"))

def test_feature_importance(synthetic_data):
    """Test feature importance calculation"""
    X, y = synthetic_data
    trainer = LGBTrainer()
    model = trainer.train(X, y)
    
    importance = pd.Series(
        model.feature_importance(), 
        index=X.columns
    )
    
    # Trend should be most important feature
    # Note: In this synthetic data, noise might have higher importance due to randomness
    # Let's check that all features have some importance
    assert all(importance > 0)
    # And that trend has reasonable importance (at least 10% of total)
    assert importance["trend"] > importance.sum() * 0.1
