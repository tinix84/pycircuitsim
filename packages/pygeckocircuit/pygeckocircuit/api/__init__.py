"""FastAPI sync proxy for GeckoCIRCUITS.

Provides a blocking POST /api/v1/simulations/sync endpoint that wraps
the async GeckoCIRCUITS submit → poll → results flow, matching the
pyplecs sync interface exactly.

Usage:
    from pygeckocircuit.api import create_api_app
    app = create_api_app()
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pygeckocircuit.gecko_server import GeckoServer
from pygeckocircuit.launcher import ensure_gecko_running

from .simulation_sync import router as sync_router

logger = logging.getLogger(__name__)

# Global client instance (initialised at startup)
gecko_server: Optional[GeckoServer] = None


def _load_config() -> dict:
    """Load config from default.yml."""
    config_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "config", "default.yml"),
        os.path.expanduser("~/.pygeckocircuit/config.yml"),
    ]
    for p in config_paths:
        if os.path.exists(p):
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {}


def create_api_app() -> FastAPI:
    """Create the FastAPI application."""
    cfg = _load_config()
    gecko_cfg = cfg.get("gecko", {})

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global gecko_server

        base_url = gecko_cfg.get("base_url", "http://172.31.64.1:8080/gecko")
        jar_path = gecko_cfg.get("jar_path", r"C:\Users\tinix\Downloads\GeckoCIRCUITS\gecko-rest-api-1.0.0.jar")
        auto_launch = gecko_cfg.get("auto_launch", True)
        timeout = float(gecko_cfg.get("timeout", 120))
        poll_interval = float(gecko_cfg.get("poll_interval", 0.5))

        # Ensure Gecko backend is running
        if auto_launch:
            ensure_gecko_running(
                base_url=base_url,
                jar_path=jar_path,
                auto_launch=True,
            )

        gecko_server = GeckoServer(
            base_url=base_url,
            timeout=timeout,
            poll_interval=poll_interval,
        )
        logger.info("GeckoServer initialized (backend=%s)", base_url)

        yield

        gecko_server.close()
        logger.info("GeckoServer closed")

    app = FastAPI(
        title="PyGeckoCIRCUITS",
        description="Synchronous REST proxy for GeckoCIRCUITS circuit simulation",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(sync_router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        if gecko_server is None:
            return {"status": "starting"}
        hc = gecko_server.health_check()
        return {"status": "ok" if hc["available"] else "degraded", "gecko": hc}

    return app


# Module-level app for uvicorn
app = create_api_app()


def main():
    """Entry point for ``pygeckocircuit-api`` console script."""
    cfg = _load_config()
    api_cfg = cfg.get("api", {})
    host = api_cfg.get("host", "0.0.0.0")
    port = int(api_cfg.get("port", 8082))
    logger.info("Starting pygeckocircuit API on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port)
