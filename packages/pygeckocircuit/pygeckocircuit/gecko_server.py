"""GeckoCIRCUITS REST API client implementing SimulationServer ABC.

Wraps the async multi-step flow (submit -> poll -> get results) into
a single blocking ``simulate()`` call.

Default backend: http://172.31.64.1:8080/gecko
"""

from __future__ import annotations

import logging
import time as _time
from typing import Any

import httpx

from pycircuitsim_core.models import SimulationRequest, SimulationResult
from pycircuitsim_core.server import SimulationServer

logger = logging.getLogger(__name__)


class GeckoServer(SimulationServer):
    """Python client for the GeckoCIRCUITS REST API.

    Implements ``pycircuitsim_core.SimulationServer`` ABC so it can be used
    interchangeably with ``pyplecs.PlecsServer`` in tool-agnostic scripts.

    Parameters
    ----------
    base_url
        Gecko REST API base URL (e.g. ``http://172.31.64.1:8080/gecko``).
    timeout
        Maximum wait time for a simulation to complete (seconds).
    poll_interval
        Seconds between status polls while simulation is running.
    """

    def __init__(
        self,
        base_url: str = "http://172.31.64.1:8080/gecko",
        timeout: float = 120.0,
        poll_interval: float = 0.5,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._client = httpx.Client(timeout=timeout)

    # ── SimulationServer ABC ─────────────────────────────────────

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        """Submit a simulation, poll until done, return result."""
        circuit_file = request.model_file
        sim_time = request.simulation_time or request.options.get("simulation_time", 1e-3)
        time_step = request.time_step or request.options.get("time_step", 1e-7)
        solver_type = request.options.get("solver_type", "backward-euler")

        # Build Gecko-specific payload
        payload = {
            "circuitFile": circuit_file,
            "simulationTime": sim_time,
            "timeStep": time_step,
            "parameters": request.parameters,
            "solverType": solver_type,
        }

        logger.info("Submitting simulation for %s", circuit_file)
        resp = self._client.post(f"{self.base_url}/api/v1/simulations", json=payload)
        resp.raise_for_status()
        submit_data = resp.json()

        sim_id = submit_data["simulationId"]
        status = submit_data.get("status", "PENDING")
        logger.info("Simulation %s submitted (status=%s)", sim_id, status)

        # Poll until COMPLETED or FAILED
        deadline = _time.monotonic() + self.timeout
        poll_data = submit_data

        while status in ("PENDING", "RUNNING"):
            if _time.monotonic() > deadline:
                return SimulationResult(
                    task_id=sim_id,
                    success=False,
                    error_message=f"Timeout after {self.timeout}s (status={status})",
                    metadata={"simulationId": sim_id},
                )
            _time.sleep(self.poll_interval)

            poll_resp = self._client.get(f"{self.base_url}/api/v1/simulations/{sim_id}")
            poll_resp.raise_for_status()
            poll_data = poll_resp.json()
            status = poll_data.get("status", "UNKNOWN")
            logger.debug("Poll %s: status=%s", sim_id, status)

        if status == "FAILED":
            return SimulationResult(
                task_id=sim_id,
                success=False,
                error_message=poll_data.get("errorMessage", "Simulation failed"),
                metadata={"simulationId": sim_id},
            )

        # Extract results
        results = poll_data.get("results", {})
        time_data = results.pop("time", [])
        signals = {name: list(vals) for name, vals in results.items()}

        execution_time = poll_data.get("executionTimeMs")
        logger.info("Simulation %s completed in %s ms (%d signals)", sim_id, execution_time, len(signals))

        return SimulationResult(
            task_id=sim_id,
            success=True,
            time=time_data,
            signals=signals,
            execution_time_ms=execution_time,
            metadata={"simulationId": sim_id, "status": status},
        )

    def simulate_batch(self, requests: list[SimulationRequest]) -> list[SimulationResult]:
        """Run multiple simulations sequentially (Gecko REST API doesn't have native batch).

        For true parallel execution, use the orchestrator with batch grouping.
        """
        results = []
        for req in requests:
            results.append(self.simulate(req))
        return results

    def is_available(self) -> bool:
        """Check if GeckoCIRCUITS REST API is reachable."""
        try:
            resp = self._client.get(f"{self.base_url}/api/v1/simulations", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def health_check(self) -> dict[str, Any]:
        """Return health info from the Gecko API."""
        try:
            resp = self._client.get(f"{self.base_url}/api/v1/simulations", timeout=5.0)
            data = resp.json()
            return {
                "available": True,
                "status_code": resp.status_code,
                "total_simulations": data.get("total", 0),
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def close(self):
        self._client.close()
