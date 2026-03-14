"""pycircuitsim-core — Shared interfaces for circuit simulation tools.

Provides abstract base classes that both pyplecs and pygeckocircuit implement,
enabling tool-agnostic simulation scripts.
"""

from pycircuitsim_core.models import (
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
    SyncSimulationRequest,
    SyncSimulationResponse,
    TaskPriority,
)
from pycircuitsim_core.server import SimulationServer
from pycircuitsim_core.cache import SimulationCacheBase
from pycircuitsim_core.orchestration import SimulationOrchestratorBase
from pycircuitsim_core.config import ConfigManagerBase

__version__ = "1.0.0"

__all__ = [
    "SimulationServer",
    "SimulationCacheBase",
    "SimulationOrchestratorBase",
    "ConfigManagerBase",
    "SimulationRequest",
    "SimulationResult",
    "SimulationStatus",
    "SyncSimulationRequest",
    "SyncSimulationResponse",
    "TaskPriority",
]
