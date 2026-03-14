"""Auto-launch GeckoCIRCUITS REST API (cross-platform).

Supports:
- Linux/macOS: subprocess.Popen with java -jar
- WSL2: PowerShell.exe Start-Process (launches on Windows host)
- Windows: subprocess.Popen with java -jar

Default backend URL: http://localhost:8080/gecko
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import time as _time

import httpx

logger = logging.getLogger(__name__)

DEFAULT_JAR_PATH = "gecko-rest-api-1.0.0.jar"
DEFAULT_GECKO_URL = "http://localhost:8080/gecko"
DEFAULT_MAX_WAIT = 30.0
DEFAULT_POLL_INTERVAL = 1.0


def _is_wsl() -> bool:
    """Detect if running inside WSL."""
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


def _is_gecko_alive(base_url: str, timeout: float = 3.0) -> bool:
    """Check if GeckoCIRCUITS REST API is reachable."""
    try:
        resp = httpx.get(f"{base_url}/api/v1/simulations", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def _launch_native(jar_path: str) -> subprocess.Popen:
    """Launch GeckoCIRCUITS JAR via java -jar (Linux/macOS/Windows)."""
    java_cmd = shutil.which("java")
    if not java_cmd:
        raise FileNotFoundError("Java not found in PATH. Install JDK 21+.")

    logger.info("Launching GeckoCIRCUITS: java -jar %s", jar_path)
    return subprocess.Popen(
        [java_cmd, "-jar", jar_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _launch_powershell(jar_path: str) -> subprocess.Popen:
    """Launch GeckoCIRCUITS JAR via PowerShell.exe from WSL."""
    ps_cmd = f'Start-Process java -ArgumentList "-jar","{jar_path}" -WindowStyle Minimized'
    logger.info("Launching GeckoCIRCUITS via PowerShell: %s", ps_cmd)
    return subprocess.Popen(
        ["powershell.exe", "-Command", ps_cmd],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def ensure_gecko_running(
    base_url: str = DEFAULT_GECKO_URL,
    jar_path: str = DEFAULT_JAR_PATH,
    max_wait: float = DEFAULT_MAX_WAIT,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    auto_launch: bool = True,
) -> bool:
    """Ensure GeckoCIRCUITS REST API is running.

    Auto-detects platform:
    - WSL2: launches via PowerShell.exe on Windows host
    - Linux/macOS/Windows: launches via java -jar

    Parameters
    ----------
    base_url
        GeckoCIRCUITS REST API base URL.
    jar_path
        Path to the gecko-rest-api JAR file.
    max_wait
        Maximum seconds to wait for startup.
    poll_interval
        Seconds between health check polls.
    auto_launch
        If True, attempt to start Gecko if not running.

    Returns
    -------
    bool
        True if Gecko is available (already running or just started).
    """
    if _is_gecko_alive(base_url):
        logger.info("GeckoCIRCUITS already running at %s", base_url)
        return True

    if not auto_launch:
        logger.warning("GeckoCIRCUITS not available at %s (auto_launch=False)", base_url)
        return False

    # Auto-detect launch method
    logger.info("GeckoCIRCUITS not running. Auto-launching...")
    if _is_wsl():
        _launch_powershell(jar_path)
    else:
        _launch_native(jar_path)

    # Wait for startup
    deadline = _time.monotonic() + max_wait
    while _time.monotonic() < deadline:
        _time.sleep(poll_interval)
        if _is_gecko_alive(base_url):
            logger.info("GeckoCIRCUITS started successfully at %s", base_url)
            return True
        logger.debug("Waiting for GeckoCIRCUITS... (%.0fs remaining)", deadline - _time.monotonic())

    logger.error("GeckoCIRCUITS failed to start within %.0fs", max_wait)
    return False
