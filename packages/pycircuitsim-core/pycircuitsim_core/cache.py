"""Abstract base class for simulation caching."""

from __future__ import annotations

import hashlib
import json
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

import pandas as pd


class SimulationCacheBase(ABC):
    """Abstract simulation cache interface.

    Implementations provide tool-specific cache backends (file, Redis, etc.)
    while sharing the hash computation and public API.
    """

    @abstractmethod
    def get_cached_result(
        self, model_file: str, parameters: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Get cached result for a model+parameters combination.

        Returns
        -------
        dict with 'timeseries' (DataFrame) and 'metadata' (dict), or None.
        """

    @abstractmethod
    def cache_result(
        self,
        model_file: str,
        parameters: dict[str, Any],
        timeseries_data: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> str:
        """Cache a simulation result.

        Returns
        -------
        Simulation hash string for this cached entry.
        """

    @abstractmethod
    def invalidate_cache(self, model_file: str, parameters: dict[str, Any]) -> bool:
        """Invalidate a specific cache entry. Returns True if found and deleted."""

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear all cached results."""

    @abstractmethod
    def get_cache_stats(self) -> dict[str, Any]:
        """Return cache usage statistics."""

    @staticmethod
    def compute_hash(
        model_file: str,
        parameters: dict[str, Any],
        include_file_content: bool = True,
        algorithm: str = "sha256",
    ) -> str:
        """Compute deterministic hash for a simulation configuration.

        Hash = SHA-256(model_path + file_content + sorted_params_JSON)
        """
        hasher = hashlib.new(algorithm)
        hasher.update(str(model_file).encode())

        if include_file_content and os.path.exists(model_file):
            with open(model_file, "rb") as f:
                hasher.update(f.read())

        param_str = json.dumps(parameters, sort_keys=True, default=str)
        hasher.update(param_str.encode())

        return hasher.hexdigest()
