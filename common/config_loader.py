"""YAML configuration loading with optional local overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_yaml(path: Path | str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}, got {type(data).__name__}")
    return data


def load_config(
    main_path: Path | str = "config/aegisos.yaml",
    local_path: Path | str = "config/local.yaml",
) -> dict[str, Any]:
    """Load main config and merge referenced sub-configs and optional local overrides."""
    main = Path(main_path)
    project_root = main.parent.parent
    cfg = load_yaml(main)

    config_files = cfg.get("monitoring", {}).get("config_files", {})
    for key, rel_path in config_files.items():
        sub_path = Path(rel_path)
        if not sub_path.is_absolute():
            sub_path = project_root / sub_path
        cfg[key] = load_yaml(sub_path)

    local = Path(local_path)
    if not local.is_absolute():
        local = project_root / local
    if local.exists():
        cfg = _deep_merge(cfg, load_yaml(local))

    return cfg
