from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | Path | None = None) -> Dict[str, Any]:
    """Load YAML config and .env variables.

    The function keeps environment loading centralized so scripts and the
    Streamlit app behave consistently.
    """

    load_dotenv(PROJECT_ROOT / ".env")
    config_path = Path(path) if path else PROJECT_ROOT / "config.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path
