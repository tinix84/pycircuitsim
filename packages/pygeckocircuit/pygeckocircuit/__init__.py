"""PyGeckoCIRCUITS — Python wrapper for GeckoCIRCUITS circuit simulation.

Provides a synchronous REST API client that wraps the GeckoCIRCUITS
async REST API (Spring Boot), giving callers the same blocking
POST-and-get-results interface as pyplecs.

Implements pycircuitsim-core ABCs for tool-agnostic scripts.
"""

from pycircuitsim_core.models import (
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
    SyncSimulationRequest,
    SyncSimulationResponse,
)

from pygeckocircuit.gecko_server import GeckoServer
from pygeckocircuit.launcher import ensure_gecko_running

__version__ = "1.1.0"

__all__ = [
    "GeckoServer",
    "SimulationRequest",
    "SimulationResult",
    "SimulationStatus",
    "SyncSimulationRequest",
    "SyncSimulationResponse",
    "ensure_gecko_running",
]
