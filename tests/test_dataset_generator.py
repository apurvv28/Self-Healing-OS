"""Tests for dataset_generator module."""

import tempfile
from pathlib import Path

from ai.dataset_generator import generate_dataset


def test_generate_dataset():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test_logs.csv"
        manifest_path = Path(tmpdir) / "test_manifest.json"

        df = generate_dataset(
            output_csv=csv_path,
            manifest_json=manifest_path,
            samples_per_class=10,
        )

        assert len(df) == 70
        assert csv_path.exists()
        assert manifest_path.exists()
        assert "log_message" in df.columns
        assert "label" in df.columns
        assert df["label"].nunique() == 7
