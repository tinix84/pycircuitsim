"""Basic tests for pygeckocircuit package."""

from __future__ import annotations

import pytest


def _gecko_available() -> bool:
    """Check if Gecko REST API is reachable."""
    try:
        import httpx

        resp = httpx.get("http://localhost:8080/gecko/api/v1/simulations", timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False


def test_import():
    """Package can be imported."""
    import pygeckocircuit

    assert pygeckocircuit.__version__ == "1.1.0"


def test_shared_models():
    """Shared models from pycircuitsim-core work."""
    from pycircuitsim_core.models import (
        SimulationRequest,
        SimulationResult,
        SyncSimulationRequest,
        SyncSimulationResponse,
    )

    req = SimulationRequest(
        model_file="test.ipes",
        parameters={"R1": 10.0},
        simulation_time=1e-3,
        time_step=1e-7,
    )
    assert req.model_file == "test.ipes"

    sync_req = SyncSimulationRequest(
        model_file="test.ipes",
        parameters={"L.1.inductance": 20e-6},
    )
    assert sync_req.model_file == "test.ipes"

    sync_resp = SyncSimulationResponse(
        success=True,
        time=[0.0, 1e-6],
        signals={"v_out": [0.0, 5.0]},
    )
    assert sync_resp.success


def test_gecko_server_init():
    """GeckoServer can be instantiated."""
    from pygeckocircuit.gecko_server import GeckoServer

    server = GeckoServer(base_url="http://localhost:8080/gecko")
    assert server.base_url == "http://localhost:8080/gecko"
    server.close()


def test_gecko_server_is_simulation_server():
    """GeckoServer implements SimulationServer ABC."""
    from pycircuitsim_core.server import SimulationServer
    from pygeckocircuit.gecko_server import GeckoServer

    assert issubclass(GeckoServer, SimulationServer)


def test_config():
    """Config loader works."""
    from pygeckocircuit.config import load_config

    cfg = load_config()
    assert isinstance(cfg, dict)


def test_cache_init():
    """GeckoCache can be instantiated."""
    import tempfile

    from pygeckocircuit.cache import GeckoCache

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = GeckoCache(cache_dir=tmpdir)
        stats = cache.get_cache_stats()
        assert stats["total_entries"] == 0


def test_data_file_exists():
    """simple_buck_prb.ipes exists in data/."""
    from pathlib import Path

    data_dir = Path(__file__).parent.parent / "data"
    assert (data_dir / "simple_buck_prb.ipes").exists()


@pytest.mark.skipif(not _gecko_available(), reason="GeckoCIRCUITS not running")
def test_gecko_health():
    """GeckoServer health check (skip if not running)."""
    from pygeckocircuit.gecko_server import GeckoServer

    server = GeckoServer()
    hc = server.health_check()
    assert hc["available"]
    server.close()
