import pytest
import json
import numpy as np
from pathlib import Path
from features.crypto_workflow.model_io import save_model, load_model

class DummyModel:
    """Simple model class for testing."""
    def __init__(self, coef):
        self.coef = coef
    
    def predict(self, X):
        return X * self.coef

def test_save_load_model_basic(tmp_path):
    """Test basic model save and load without metadata."""
    model_path = tmp_path / "model.joblib"
    model = DummyModel(coef=2.0)
    
    # Save model
    save_model(model, str(model_path))
    assert model_path.exists()
    
    # Load and verify
    loaded_model, metadata = load_model(str(model_path))
    assert isinstance(loaded_model, DummyModel)
    assert loaded_model.coef == 2.0
    assert metadata == {}  # No metadata expected
    
    # Verify predictions match
    X = np.array([1.0, 2.0, 3.0])
    np.testing.assert_array_equal(
        model.predict(X),
        loaded_model.predict(X)
    )

def test_save_load_model_with_metadata(tmp_path):
    """Test model save/load with metadata."""
    model_path = tmp_path / "model.joblib"
    model = DummyModel(coef=3.0)
    metadata = {
        "version": "1.0",
        "params": {"coef": 3.0},
        "metrics": {"mse": 0.1}
    }
    
    # Save with metadata
    save_model(model, str(model_path), metadata)
    assert model_path.exists()
    assert model_path.with_suffix('.json').exists()
    
    # Load and verify
    loaded_model, loaded_metadata = load_model(str(model_path))
    assert isinstance(loaded_model, DummyModel)
    assert loaded_metadata == metadata

def test_save_model_creates_dirs(tmp_path):
    """Test save_model creates intermediate directories."""
    nested_path = tmp_path / "models" / "subdir" / "model.joblib"
    model = DummyModel(coef=1.0)
    
    save_model(model, str(nested_path))
    assert nested_path.exists()

def test_save_model_atomic(tmp_path):
    """Test atomic write behavior."""
    model_path = tmp_path / "model.joblib"
    model = DummyModel(coef=1.0)
    metadata = {"version": "1.0"}
    
    # Create a file at target path
    model_path.parent.mkdir(exist_ok=True)
    model_path.touch()
    
    # Save should succeed and replace existing file
    save_model(model, str(model_path), metadata)
    assert model_path.exists()
    
    loaded_model, loaded_metadata = load_model(str(model_path))
    assert isinstance(loaded_model, DummyModel)
    assert loaded_metadata == metadata

def test_load_model_missing_file():
    """Test load_model with non-existent file."""
    with pytest.raises(FileNotFoundError):
        load_model("/nonexistent/path/model.joblib")

def test_load_model_corrupted_metadata(tmp_path):
    """Test load_model with corrupted metadata file."""
    model_path = tmp_path / "model.joblib"
    model = DummyModel(coef=1.0)
    
    # Save model
    save_model(model, str(model_path), {"version": "1.0"})
    
    # Corrupt metadata file
    with open(model_path.with_suffix('.json'), 'w') as f:
        f.write("invalid json")
    
    # Should raise JSONDecodeError
    with pytest.raises(json.JSONDecodeError):
        load_model(str(model_path))
