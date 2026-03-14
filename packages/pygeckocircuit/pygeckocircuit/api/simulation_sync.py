"""Synchronous simulation endpoint — POST /api/v1/simulations/sync.

Wraps the async GeckoCIRCUITS REST API (submit -> poll -> results) into
a single blocking request-response, matching pyplecs' sync endpoint.

Special parameter keys prefixed with ``_`` are extracted as simulation settings:
    - ``_simulationTime``: total simulation duration (default 1e-3)
    - ``_timeStep``: solver time step (default 1e-7)
    - ``_solverType``: solver type (default "backward-euler")
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from pycircuitsim_core.models import (
    SimulationRequest,
    SyncSimulationRequest,
    SyncSimulationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/simulations/sync",
    response_model=SyncSimulationResponse,
    summary="Run a synchronous GeckoCIRCUITS simulation",
    description="Submits, polls, and returns results in a single blocking call.",
)
async def simulate_sync(req: SyncSimulationRequest) -> SyncSimulationResponse:
    """Synchronous simulation: submit -> poll -> return results."""
    from pygeckocircuit.api import gecko_server

    if gecko_server is None:
        raise HTTPException(status_code=503, detail="GeckoServer not initialized")

    # Extract simulation settings from parameters
    params = dict(req.parameters)
    sim_time = params.pop("_simulationTime", 1e-3)
    time_step = params.pop("_timeStep", 1e-7)
    solver_type = params.pop("_solverType", "backward-euler")

    # Build shared request
    gecko_req = SimulationRequest(
        model_file=req.model_file,
        parameters=params,
        simulation_time=sim_time,
        time_step=time_step,
        options={"solver_type": str(solver_type)},
    )

    logger.info("Sync simulation: model=%s, T_sim=%.2e, dt=%.2e, %d params", req.model_file, sim_time, time_step, len(params))

    result = gecko_server.simulate(gecko_req)

    if not result.success:
        return SyncSimulationResponse(
            success=False,
            error_message=result.error_message,
            metadata=result.metadata,
        )

    # Apply signal name map if provided
    signals = result.signals
    if req.signal_map:
        signals = {req.signal_map.get(name, name): vals for name, vals in signals.items()}

    return SyncSimulationResponse(
        success=True,
        time=result.time,
        signals=signals,
        metadata={
            "simulationId": result.task_id,
            "executionTimeMs": result.execution_time_ms,
            "source": "pygeckocircuit",
        },
    )
