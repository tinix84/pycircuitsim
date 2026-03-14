"""Configuration management for pygeckocircuit.

Extends pycircuitsim-core ConfigManagerBase with GeckoCIRCUITS-specific settings.
Also provides backward-compatible load_config() function.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml

from pycircuitsim_core.config import ConfigManagerBase

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.yml"


class GeckoConfigManager(ConfigManagerBase):
    """Config manager for pygeckocircuit."""

    def _find_config_file(self) -> str:
        search_paths = [
            "./config/default.yml",
            str(_DEFAULT_CONFIG_PATH),
            os.path.expanduser("~/.pygeckocircuit/config.yml"),
        ]
        for p in search_paths:
            if Path(p).exists():
                return p
        return str(_DEFAULT_CONFIG_PATH)


# ── Backward-compatible convenience functions ────────────────────

def load_config(config_path: str | Path | None = None) -> dict:
    """Load configuration from YAML file.

    Search order:
    1. Explicit path (if provided)
    2. ./config/default.yml (relative to package root)
    3. ~/.pygeckocircuit/config.yml
    """
    search_paths = [
        config_path,
        _DEFAULT_CONFIG_PATH,
        Path(os.path.expanduser("~/.pygeckocircuit/config.yml")),
    ]
    for p in search_paths:
        if p is not None and Path(p).exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {}


def get_gecko_url(config: dict | None = None) -> str:
    if config is None:
        config = load_config()
    return config.get("gecko", {}).get("base_url", "http://localhost:8080/gecko")


def get_api_port(config: dict | None = None) -> int:
    if config is None:
        config = load_config()
    return int(config.get("api", {}).get("port", 8082))
