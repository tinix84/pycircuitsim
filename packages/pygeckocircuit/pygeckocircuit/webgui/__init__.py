"""Web GUI for pygeckocircuit — FastAPI + Jinja2 dashboard.

Provides a monitoring dashboard with WebSocket real-time updates
for simulation status, cache stats, and orchestrator health.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import uvicorn
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


class WebSocketManager:
    """Manages active WebSocket connections for real-time updates."""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        import json

        msg = json.dumps(data)
        for ws in self.active[:]:
            try:
                await ws.send_text(msg)
            except Exception:
                self.active.remove(ws)


ws_manager = WebSocketManager()


def create_web_app() -> "FastAPI":
    """Create the FastAPI web GUI application."""
    if not HAS_FASTAPI:
        raise ImportError("Install pygeckocircuit[api] for web GUI support")

    @asynccontextmanager
    async def lifespan(app):
        yield

    app = FastAPI(
        title="PyGeckoCIRCUITS Dashboard",
        version="1.1.0",
        lifespan=lifespan,
    )

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return """
        <!DOCTYPE html>
        <html>
        <head><title>PyGeckoCIRCUITS Dashboard</title>
        <style>
            body { font-family: system-ui; margin: 2rem; background: #1a1a2e; color: #eee; }
            h1 { color: #e94560; }
            .card { background: #16213e; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
            .stat { font-size: 2rem; font-weight: bold; color: #0f3460; }
        </style>
        </head>
        <body>
            <h1>PyGeckoCIRCUITS Dashboard</h1>
            <div class="card"><h2>Status</h2><p>Dashboard active. Connect to WebSocket at /ws for real-time updates.</p></div>
            <div class="card"><h2>API</h2><p>REST API docs at <a href="/docs">/docs</a></p></div>
        </body>
        </html>
        """

    @app.get("/api/status")
    async def status():
        return {"status": "ok", "websocket_clients": len(ws_manager.active)}

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws_manager.connect(ws)
        try:
            while True:
                data = await ws.receive_text()
                if data == "ping":
                    await ws.send_text("pong")
        except WebSocketDisconnect:
            ws_manager.disconnect(ws)

    return app


def run_app(host: str = "0.0.0.0", port: int = 8083):
    """Entry point for pygeckocircuit-gui."""
    if not HAS_FASTAPI:
        print("Error: Install pygeckocircuit[api] for web GUI support")
        return
    app = create_web_app()
    uvicorn.run(app, host=host, port=port)
