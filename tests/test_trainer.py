"""Tests for ModelTrainer module."""

import tempfile
from pathlib import Path

from ai.trainer import ModelTrainer


def test_trainer_pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_dir = Path(tmpdir) / "models"
        csv_path = Path(tmpdir) / "test_logs.csv"

        trainer = ModelTrainer(model_dir=model_dir)
        metrics = trainer.train_and_evaluate(csv_path=csv_path)

        assert "model_name" in metrics
        assert "macro_f1" in metrics
        assert metrics["macro_f1"] > 0.80
        assert (model_dir / "failure_classifier.joblib").exists()
        assert (model_dir / "model_metadata.json").exists()
