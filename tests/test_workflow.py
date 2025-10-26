# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import unittest
from pathlib import Path
import shutil

from qlib.workflow import R
from qlib.tests import TestAutoData
import pytest
import pandas as pd
import numpy as np
from qlib.scripts.data_collector.crypto.collector import CryptoCollector
from qlib.features.crypto import generate_features
from qlib.model.crypto import LGBTrainer


class WorkflowTest(TestAutoData):
    # Creating the directory manually doesn't work with mlflow,
    # so we add a subfolder named .trash when we create the directory.
    TMP_PATH = Path("./.mlruns_tmp/.trash")

    def tearDown(self) -> None:
        if self.TMP_PATH.exists():
            shutil.rmtree(self.TMP_PATH)

    def test_get_local_dir(self):
        """ """
        self.TMP_PATH.mkdir(parents=True, exist_ok=True)

        with R.start(uri=str(self.TMP_PATH)):
            pass

        with R.uri_context(uri=str(self.TMP_PATH)):
            resume_recorder = R.get_recorder()
            resume_recorder.get_local_dir()

    @pytest.mark.integration
    def test_end_to_end_workflow(self, test_data_dir, config_for_test, sample_ohlcv_data):
        """Test complete workflow from data collection to signal generation"""
        # 1. Data Collection
        collector = CryptoCollector(save_dir=test_data_dir, interval="15min")
        df_raw = sample_ohlcv_data.copy()
        df_validated, report = collector.validate_data(df_raw)
        assert report["valid_rows"] > 0

        # 2. Feature Generation
        features = generate_features(df_validated)
        assert len(features) > 0
        assert "target" in features.columns

        # 3. Model Training
        train_cutoff = int(len(features) * 0.8)
        X_train = features.iloc[:train_cutoff].drop("target", axis=1)
        y_train = features.iloc[:train_cutoff]["target"]
        X_val = features.iloc[train_cutoff:].drop("target", axis=1)
        y_val = features.iloc[train_cutoff:]["target"]

        trainer = LGBTrainer()
        model, metrics = trainer.train_validate(X_train, y_train, X_val, y_val)
        assert metrics["accuracy"] > 0.5
        assert metrics["sharpe"] > 0

        # 4. Signal Generation
        predictions = model.predict(X_val)
        signals = pd.Series(predictions, index=X_val.index)
        assert len(signals) == len(X_val)
        assert signals.between(0, 1).all()


if __name__ == "__main__":
    unittest.main()
