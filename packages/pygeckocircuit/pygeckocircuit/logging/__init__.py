"""Structured logging for pygeckocircuit.

Implements pycircuitsim-core StructuredLoggerBase with structlog-based
console, rotating file, and structured JSON logging.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Optional

from pycircuitsim_core.logging import StructuredLoggerBase

try:
    import structlog

    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


class GeckoLogger(StructuredLoggerBase):
    """Structured logger for pygeckocircuit."""

    def __init__(
        self,
        level: str = "INFO",
        log_file: Optional[str] = None,
        structured_file: Optional[str] = None,
    ):
        self._stdlib_logger = logging.getLogger("pygeckocircuit")
        self._stdlib_logger.setLevel(getattr(logging, level))

        # Clear existing handlers
        for h in self._stdlib_logger.handlers[:]:
            self._stdlib_logger.removeHandler(h)

        # Console handler
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(getattr(logging, level))
        console.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        self._stdlib_logger.addHandler(console)

        # File handler
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            fh = logging.handlers.RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
            fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            self._stdlib_logger.addHandler(fh)

        # Structured JSON handler
        if structured_file:
            Path(structured_file).parent.mkdir(parents=True, exist_ok=True)
            jh = logging.handlers.RotatingFileHandler(structured_file, maxBytes=10 * 1024 * 1024, backupCount=5)
            jh.setFormatter(_JsonFormatter())
            self._stdlib_logger.addHandler(jh)

        # Structlog integration (if available)
        if HAS_STRUCTLOG:
            structlog.configure(
                processors=[
                    structlog.stdlib.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.JSONRenderer(),
                ],
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            self._slog = structlog.get_logger("pygeckocircuit")
        else:
            self._slog = None

    def _log(self, level: str, message: str, **kwargs):
        if self._slog:
            getattr(self._slog, level)(message, **kwargs)
        else:
            getattr(self._stdlib_logger, level)(message, extra=kwargs)

    def log_simulation_start(self, task_id, model_file, parameters, worker_id=None):
        self._log("info", "Simulation started", task_id=task_id, model_file=model_file, params=len(parameters))

    def log_simulation_complete(self, task_id, success, execution_time, worker_id=None, cached=False):
        self._log("info", "Simulation completed", task_id=task_id, success=success, time=execution_time, cached=cached)

    def log_simulation_error(self, task_id, error_message, worker_id=None):
        self._log("error", "Simulation failed", task_id=task_id, error=error_message)

    def log_cache_hit(self, task_id, simulation_hash, model_file):
        self._log("info", "Cache hit", task_id=task_id, hash=simulation_hash)

    def log_cache_miss(self, task_id, simulation_hash, model_file):
        self._log("info", "Cache miss", task_id=task_id, hash=simulation_hash)

    def log_api_request(self, endpoint, method, status_code, response_time, client_ip=None):
        self._log("info", "API request", endpoint=endpoint, method=method, status=status_code, time=response_time)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": record.created,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(entry)


# Global singleton
_logger: Optional[GeckoLogger] = None


def get_logger() -> GeckoLogger:
    global _logger
    if _logger is None:
        _logger = GeckoLogger()
    return _logger


def init_logging(level: str = "INFO", log_file: Optional[str] = None, structured_file: Optional[str] = None) -> GeckoLogger:
    global _logger
    _logger = GeckoLogger(level=level, log_file=log_file, structured_file=structured_file)
    return _logger
