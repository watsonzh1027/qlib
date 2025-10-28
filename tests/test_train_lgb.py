import pytest
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from features.crypto_workflow.model_io import load_model
from examples.train_lgb import train_from_features, main

def make_sample_features(n=200):
    dates = pd.date_range("2023-01-01", periods=n, freq="1h")
    np.random.seed(0)
    close = 100 + np.random.randn(n).cumsum()
    df = pd.DataFrame({
        "open": close + np.random.randn(n) * 0.1,
        "high": close + np.abs(np.random.randn(n)) * 0.2,
        "low": close - np.abs(np.random.randn(n)) * 0.2,
        "close": close,
        "volume": np.random.randint(1000, 10000, n),
    }, index=dates)
    # basic returns feature used by trainer
    df["returns"] = df["close"].pct_change()
    # add a simple moving average feature
    df["ma_5"] = df["close"].rolling(5).mean()
    df = df.fillna(method="bfill").fillna(0)
    return df

def test_train_lgb_end_to_end(tmp_path):
    """Train on synthetic features and verify model + report saved and model can predict."""
    feat_path = tmp_path / "features.parquet"
    model_dir = tmp_path / "models"
    model_dir.mkdir()

    df = make_sample_features(n=300)
    df.to_parquet(str(feat_path))

    result = train_from_features(str(feat_path), str(model_dir), model_name="test_model", early_stopping_rounds=10)
    model_path = Path(result["model_path"])
    report_path = Path(result["report_path"])

    assert model_path.exists(), "Model file was not created"
    assert report_path.exists(), "Training report not created"

    # Load model and do a basic predict sanity check
    model_obj, metadata = load_model(str(model_path))
    # model_obj should be LGBModel wrapper; it must support predict after training
    # Use last few rows of features to predict
    df_loaded = pd.read_parquet(str(feat_path))
    X = df_loaded.select_dtypes(include=[np.number]).iloc[-5:]
    preds = model_obj.predict(X.values)
    assert len(preds) == 5
    # predictions should be finite probabilities
    assert (preds >= 0).all() and (preds <= 1).all()


def test_missing_returns_column(tmp_path):
    """Test that ValueError is raised when 'returns' column is missing."""
    feat_path = tmp_path / "features_no_returns.parquet"
    model_dir = tmp_path / "models"
    model_dir.mkdir()

    df = make_sample_features(n=300)
    df = df.drop(columns=["returns"])
    df.to_parquet(str(feat_path))

    with pytest.raises(ValueError, match="Features must contain 'returns' column"):
        train_from_features(str(feat_path), str(model_dir))


def test_insufficient_data(tmp_path):
    """Test that ValueError is raised when data has fewer than 10 rows."""
    feat_path = tmp_path / "features_few_rows.parquet"
    model_dir = tmp_path / "models"
    model_dir.mkdir()

    df = make_sample_features(n=5)
    df.to_parquet(str(feat_path))

    with pytest.raises(ValueError, match="Not enough data to train"):
        train_from_features(str(feat_path), str(model_dir))


def test_logging_and_return_values(tmp_path, caplog):
    """Test that logging and return values are correct."""
    caplog.set_level(logging.INFO)
    feat_path = tmp_path / "features.parquet"
    model_dir = tmp_path / "models"
    model_dir.mkdir()

    df = make_sample_features(n=300)
    df.to_parquet(str(feat_path))

    result = train_from_features(str(feat_path), str(model_dir), model_name="test_model", early_stopping_rounds=10)

    # Check logging
    assert any("Trained model saved to" in message for message in caplog.messages)
    assert any("Training report saved to" in message for message in caplog.messages)

    # Check return values
    assert "model_path" in result
    assert "report_path" in result
    assert "metrics" in result
    assert Path(result["model_path"]).exists()
    assert Path(result["report_path"]).exists()


def test_main_function(tmp_path, monkeypatch):
    """Test the main function with mocked arguments."""
    feat_path = tmp_path / "features.parquet"
    model_dir = tmp_path / "models"
    model_dir.mkdir()

    df = make_sample_features(n=300)
    df.to_parquet(str(feat_path))

    # Mock sys.argv to simulate command line arguments
    import sys
    monkeypatch.setattr(sys, 'argv', ['train_lgb.py', '--features-path', str(feat_path), '--model-dir', str(model_dir)])

    # Call main function
    main()

    # Check that model and report were created
    model_files = list(model_dir.glob("*.joblib"))
    report_files = list(model_dir.glob("*_train_report.json"))
    assert len(model_files) == 1
    assert len(report_files) == 1
