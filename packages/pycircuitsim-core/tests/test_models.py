"""Tests for pycircuitsim-core shared models."""

from __future__ import annotations

import pytest

from pycircuitsim_core.models import (
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
    SyncSimulationRequest,
    SyncSimulationResponse,
    TaskPriority,
)


def test_simulation_request():
    req = SimulationRequest(
        model_file="test.ipes",
        parameters={"R1": 10.0},
        simulation_time=1e-3,
        time_step=1e-7,
    )
    assert req.model_file == "test.ipes"
    assert req.parameters["R1"] == 10.0
    assert req.options == {}


def test_simulation_result():
    result = SimulationResult(
        task_id="abc",
        success=True,
        time=[0.0, 1e-6, 2e-6],
        signals={"v_out": [0.0, 5.0, 5.1]},
    )
    assert result.success
    df = result.to_dataframe()
    assert list(df.columns) == ["time", "v_out"]
    assert len(df) == 3


def test_simulation_result_failed():
    result = SimulationResult(
        task_id="fail",
        success=False,
        error_message="Solver diverged",
    )
    assert not result.success
    assert result.error_message == "Solver diverged"


def test_simulation_status():
    assert SimulationStatus.COMPLETED == "COMPLETED"
    assert SimulationStatus.QUEUED.value == "QUEUED"


def test_task_priority_ordering():
    assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value
    assert TaskPriority.HIGH.value < TaskPriority.NORMAL.value
    assert TaskPriority.NORMAL.value < TaskPriority.LOW.value


def test_sync_request():
    req = SyncSimulationRequest(
        model_file="buck.plecs",
        parameters={"Vi": 12.0},
        signal_map={"Scope1": "v_out"},
    )
    assert req.signal_map["Scope1"] == "v_out"


def test_sync_response():
    resp = SyncSimulationResponse(
        success=True,
        time=[0.0, 1.0],
        signals={"v_out": [0.0, 5.0]},
    )
    assert resp.success
    assert resp.error_message is None
