"""Tests for YAML configuration loading."""

from pathlib import Path

from common.config_loader import load_config, load_yaml


def test_load_thresholds_yaml():
    data = load_yaml("config/thresholds.yaml")
    assert data["thresholds"]["cpu"]["critical_percent"] == 90


def test_load_config_merges_sub_configs():
    cfg = load_config("config/aegisos.yaml")
    assert cfg["aegisos"]["environment"] == "wsl"
    assert "thresholds" in cfg
    assert "confidence" in cfg
    assert "remediation" in cfg
    assert cfg["thresholds"]["thresholds"]["memory"]["critical_percent"] == 95


def test_config_files_exist():
    for path in [
        "config/aegisos.yaml",
        "config/thresholds.yaml",
        "config/confidence-policies.yaml",
        "config/remediation-policies.yaml",
    ]:
        assert Path(path).exists(), f"Missing config file: {path}"
