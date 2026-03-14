"""Tests for pycircuitsim-core cache base."""

from __future__ import annotations

import tempfile
from pathlib import Path

from pycircuitsim_core.cache import SimulationCacheBase


def test_compute_hash_deterministic():
    h1 = SimulationCacheBase.compute_hash("model.ipes", {"R1": 10.0}, include_file_content=False)
    h2 = SimulationCacheBase.compute_hash("model.ipes", {"R1": 10.0}, include_file_content=False)
    assert h1 == h2


def test_compute_hash_param_order_independent():
    h1 = SimulationCacheBase.compute_hash("m.ipes", {"A": 1.0, "B": 2.0}, include_file_content=False)
    h2 = SimulationCacheBase.compute_hash("m.ipes", {"B": 2.0, "A": 1.0}, include_file_content=False)
    assert h1 == h2


def test_compute_hash_different_params():
    h1 = SimulationCacheBase.compute_hash("m.ipes", {"R1": 10.0}, include_file_content=False)
    h2 = SimulationCacheBase.compute_hash("m.ipes", {"R1": 20.0}, include_file_content=False)
    assert h1 != h2


def test_compute_hash_includes_file_content():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ipes", delete=False) as f:
        f.write("circuit data v1")
        f.flush()
        h1 = SimulationCacheBase.compute_hash(f.name, {}, include_file_content=True)

    with open(f.name, "w") as f2:
        f2.write("circuit data v2")

    h2 = SimulationCacheBase.compute_hash(f.name, {}, include_file_content=True)
    assert h1 != h2

    Path(f.name).unlink()
