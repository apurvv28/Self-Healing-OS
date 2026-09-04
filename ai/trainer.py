"""Model training and evaluation pipeline for AegisOS AI failure classifier."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ai.dataset_generator import generate_dataset
from ai.preprocessor import LogPreprocessor

logger = logging.getLogger(__name__)


class ModelTrainer:
    """Trains, evaluates, and persists scikit-learn failure classification models."""

    def __init__(self, model_dir: str | Path = "ai/models") -> None:
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def train_and_evaluate(
        self,
        csv_path: str | Path = "data/raw/failure_logs.csv",
        random_seed: int = 42,
    ) -> dict[str, Any]:
        """Train models, evaluate performance, and save best model pipeline artifact."""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            logger.info("Dataset file %s not found. Generating dataset...", csv_file)
            generate_dataset(output_csv=csv_file)

        df = pd.read_csv(csv_file)
        X = df["log_message"]
        y = df["label"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=random_seed, stratify=y
        )

        candidates: dict[str, Pipeline] = {
            "logistic_regression": Pipeline([
                ("tfidf", LogPreprocessor.build_vectorizer()),
                ("clf", LogisticRegression(max_iter=1000, random_state=random_seed)),
            ]),
            "random_forest": Pipeline([
                ("tfidf", LogPreprocessor.build_vectorizer()),
                ("clf", RandomForestClassifier(n_estimators=100, random_state=random_seed)),
            ]),
        }

        best_name = ""
        best_f1 = -1.0
        best_pipeline: Pipeline | None = None
        best_metrics: dict[str, Any] = {}

        for name, pipeline in candidates.items():
            logger.info("Training candidate model: %s", name)
            pipeline.fit(X_train, y_train)

            y_pred = pipeline.predict(X_test)
            macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
            report = classification_report(y_test, y_pred, output_dict=True)

            logger.info("Model %s achieved Macro F1: %.4f", name, macro_f1)

            if macro_f1 > best_f1:
                best_f1 = macro_f1
                best_name = name
                best_pipeline = pipeline
                best_metrics = {
                    "model_name": name,
                    "macro_f1": macro_f1,
                    "classification_report": report,
                    "train_size": len(X_train),
                    "test_size": len(X_test),
                    "classes": list(pipeline.classes_),
                }

        if best_pipeline is None:
            raise RuntimeError("Model training failed to produce a valid pipeline.")

        # Save trained pipeline artifact
        model_path = self.model_dir / "failure_classifier.joblib"
        joblib.dump(best_pipeline, model_path)
        logger.info("Saved best model artifact to %s", model_path)

        # Save model metadata
        metadata_path = self.model_dir / "model_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as fh:
            json.dump(best_metrics, fh, indent=2)

        return best_metrics


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    trainer = ModelTrainer()
    metrics = trainer.train_and_evaluate()
    print(f"\nTraining Complete!")
    print(f"Selected Model: {metrics['model_name']}")
    print(f"Macro F1 Score: {metrics['macro_f1']:.4f}")


if __name__ == "__main__":
    main()
