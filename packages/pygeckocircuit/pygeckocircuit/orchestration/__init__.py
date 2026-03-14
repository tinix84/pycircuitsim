"""Simulation orchestration for pygeckocircuit.

Implements pycircuitsim-core SimulationOrchestratorBase with priority queuing,
caching, batch execution via GeckoCIRCUITS REST API, and retry logic.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from queue import PriorityQueue
from typing import Any, Callable, Optional

from pycircuitsim_core.models import SimulationRequest, SimulationResult, SimulationStatus, TaskPriority
from pycircuitsim_core.orchestration import SimulationOrchestratorBase

from pygeckocircuit.cache import GeckoCache

logger = logging.getLogger(__name__)


@dataclass
class SimulationTask:
    """A simulation task in the priority queue."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request: Optional[SimulationRequest] = None
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: SimulationStatus = SimulationStatus.QUEUED
    result: Optional[SimulationResult] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def __lt__(self, other):
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class GeckoOrchestrator(SimulationOrchestratorBase):
    """Orchestrates GeckoCIRCUITS simulations with caching, queuing, and retry.

    Uses GeckoServer for execution and GeckoCache for result deduplication.
    """

    def __init__(self, gecko_server=None, batch_size: int = 4, cache_dir: str = "./cache"):
        self.server = gecko_server
        self.batch_size = batch_size
        self.cache = GeckoCache(cache_dir=cache_dir)

        self.task_queue: PriorityQueue = PriorityQueue()
        self.active_tasks: dict[str, SimulationTask] = {}
        self.completed_tasks: dict[str, SimulationTask] = {}

        self.is_running = False
        self.is_processing_batch = False
        self._lock = threading.Lock()
        self._orchestrator_task: Optional[asyncio.Task] = None

        self.stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cached_hits": 0,
            "total_batches": 0,
            "queue_size": 0,
        }

        self.task_callbacks: dict[str, list[Callable]] = {
            "on_task_started": [],
            "on_task_completed": [],
            "on_task_failed": [],
            "on_queue_empty": [],
            "on_batch_started": [],
            "on_batch_completed": [],
        }

    def set_server(self, gecko_server) -> None:
        """Set or update the GeckoServer instance."""
        self.server = gecko_server

    def add_callback(self, event: str, callback: Callable) -> None:
        if event in self.task_callbacks:
            self.task_callbacks[event].append(callback)

    def remove_callback(self, event: str, callback: Callable) -> None:
        if event in self.task_callbacks and callback in self.task_callbacks[event]:
            self.task_callbacks[event].remove(callback)

    def _trigger(self, event: str, *args, **kwargs):
        for cb in self.task_callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as e:
                logger.error("Callback error for %s: %s", event, e)

    async def submit_simulation(
        self,
        request: SimulationRequest,
        priority: TaskPriority = TaskPriority.NORMAL,
        use_cache: bool = True,
    ) -> str:
        task = SimulationTask(request=request, priority=priority)

        # Check cache
        if use_cache:
            cached = self.cache.get_cached_result(request.model_file, request.parameters)
            if cached:
                task.status = SimulationStatus.COMPLETED
                task.result = SimulationResult(
                    task_id=task.id,
                    success=True,
                    time=cached["timeseries"]["time"].tolist() if "time" in cached["timeseries"] else [],
                    signals={
                        c: cached["timeseries"][c].tolist()
                        for c in cached["timeseries"].columns
                        if c != "time"
                    },
                    metadata=cached["metadata"],
                    cached=True,
                )
                task.completed_at = time.time()
                self.completed_tasks[task.id] = task
                self.stats["total_cached_hits"] += 1
                self._trigger("on_task_completed", task)
                return task.id

        with self._lock:
            self.task_queue.put(task)
            self.active_tasks[task.id] = task
            self.stats["total_submitted"] += 1

        if not self.is_running:
            await self.start()

        return task.id

    async def get_task_status(self, task_id: str) -> Optional[dict[str, Any]]:
        task = self.active_tasks.get(task_id) or self.completed_tasks.get(task_id)
        if not task:
            return None
        return {"id": task.id, "status": task.status.value, "error": task.error}

    async def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                if task.status == SimulationStatus.QUEUED:
                    task.status = SimulationStatus.CANCELLED
                    del self.active_tasks[task_id]
                    self.completed_tasks[task_id] = task
                    return True
        return False

    async def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._orchestrator_task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.is_running = False
        if self._orchestrator_task:
            self._orchestrator_task.cancel()
            try:
                await self._orchestrator_task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        try:
            while self.is_running:
                if self.is_processing_batch or self.task_queue.empty():
                    await asyncio.sleep(0.1)
                    continue

                batch = []
                while len(batch) < self.batch_size and not self.task_queue.empty():
                    try:
                        task = self.task_queue.get_nowait()
                        batch.append(task)
                    except Exception:
                        break

                if batch:
                    await self._execute_batch(batch)

        except asyncio.CancelledError:
            pass

    async def _execute_batch(self, tasks: list[SimulationTask]):
        self.is_processing_batch = True
        try:
            self._trigger("on_batch_started", tasks)

            for task in tasks:
                task.status = SimulationStatus.RUNNING
                task.started_at = time.time()
                self._trigger("on_task_started", task)

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.server.simulate_batch([t.request for t in tasks]),
            )

            for task, result in zip(tasks, results):
                task.result = result
                task.completed_at = time.time()
                if result.success:
                    task.status = SimulationStatus.COMPLETED
                    # Cache result
                    df = result.to_dataframe()
                    if not df.empty:
                        self.cache.cache_result(
                            task.request.model_file,
                            task.request.parameters,
                            df,
                            result.metadata,
                        )
                    with self._lock:
                        self.active_tasks.pop(task.id, None)
                        self.completed_tasks[task.id] = task
                        self.stats["total_completed"] += 1
                    self._trigger("on_task_completed", task)
                else:
                    await self._handle_failure(task, result.error_message or "Unknown error")

            self.stats["total_batches"] += 1
            self._trigger("on_batch_completed", tasks, results)

        except Exception as e:
            for task in tasks:
                await self._handle_failure(task, str(e))
        finally:
            self.is_processing_batch = False

    async def _handle_failure(self, task: SimulationTask, error_message: str):
        task.error = error_message
        task.retry_count += 1

        if task.retry_count < task.max_retries:
            task.status = SimulationStatus.QUEUED
            await asyncio.sleep(2)
            with self._lock:
                self.task_queue.put(task)
        else:
            task.status = SimulationStatus.FAILED
            task.completed_at = time.time()
            with self._lock:
                self.active_tasks.pop(task.id, None)
                self.completed_tasks[task.id] = task
                self.stats["total_failed"] += 1
            self._trigger("on_task_failed", task)

    def get_orchestrator_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                **self.stats,
                "queue_size": self.task_queue.qsize(),
                "cache_stats": self.cache.get_cache_stats(),
            }

    async def wait_for_completion(
        self, task_id: str, timeout: Optional[float] = None
    ) -> Optional[SimulationResult]:
        start = time.time()
        while True:
            task = self.active_tasks.get(task_id) or self.completed_tasks.get(task_id)
            if not task:
                return None
            if task.status in (SimulationStatus.COMPLETED, SimulationStatus.FAILED, SimulationStatus.CANCELLED):
                return task.result
            if timeout and (time.time() - start) > timeout:
                return None
            await asyncio.sleep(0.1)

    async def wait_for_all_tasks(self, timeout: Optional[float] = None) -> bool:
        start = time.time()
        while True:
            if self.task_queue.empty() and not self.is_processing_batch:
                return True
            if timeout and (time.time() - start) > timeout:
                return False
            await asyncio.sleep(0.1)
