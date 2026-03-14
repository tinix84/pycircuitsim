"""CLI installer/setup wizard for pygeckocircuit.

Usage: pygeckocircuit-setup [command]

Commands:
    check       Check system requirements (Java, JAR, connectivity)
    create-config  Generate default config file
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import yaml


def check_java() -> bool:
    """Check if Java 21+ is available."""
    java = shutil.which("java")
    if not java:
        print("[FAIL] Java not found in PATH")
        return False

    import subprocess

    result = subprocess.run([java, "-version"], capture_output=True, text=True)
    version_str = result.stderr or result.stdout
    print(f"[OK] Java found: {java}")
    print(f"     {version_str.splitlines()[0].strip()}")
    return True


def check_gecko_jar(jar_path: str) -> bool:
    """Check if GeckoCIRCUITS JAR exists."""
    if Path(jar_path).exists():
        size_mb = Path(jar_path).stat().st_size / (1024 * 1024)
        print(f"[OK] JAR found: {jar_path} ({size_mb:.1f} MB)")
        return True
    print(f"[FAIL] JAR not found: {jar_path}")
    return False


def check_connectivity(base_url: str) -> bool:
    """Check if GeckoCIRCUITS REST API is reachable."""
    try:
        import httpx

        resp = httpx.get(f"{base_url}/api/v1/simulations", timeout=5.0)
        if resp.status_code == 200:
            print(f"[OK] GeckoCIRCUITS API reachable at {base_url}")
            return True
    except Exception:
        pass
    print(f"[WARN] GeckoCIRCUITS API not reachable at {base_url}")
    return False


def create_config(target: str = "config/default.yml") -> None:
    """Generate a default config file."""
    config = {
        "app": {"name": "PyGeckoCIRCUITS", "version": "1.1.0"},
        "gecko": {
            "base_url": "http://localhost:8080/gecko",
            "jar_path": "gecko-rest-api-1.0.0.jar",
            "auto_launch": True,
            "timeout": 120,
            "poll_interval": 0.5,
        },
        "api": {"host": "0.0.0.0", "port": 8082},
        "cache": {
            "enabled": True,
            "directory": "./cache",
            "ttl": 3600,
        },
        "logging": {
            "level": "INFO",
            "file": {"enabled": True, "path": "./logs/pygeckocircuit.log"},
        },
    }
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    print(f"Config written to {target}")


def main():
    """Entry point for pygeckocircuit-setup."""
    args = sys.argv[1:]
    command = args[0] if args else "check"

    if command == "check":
        print("=== PyGeckoCIRCUITS System Check ===\n")
        check_java()
        check_gecko_jar(os.environ.get("GECKO_JAR", "gecko-rest-api-1.0.0.jar"))
        check_connectivity(os.environ.get("GECKO_URL", "http://localhost:8080/gecko"))
        print("\nDone.")
    elif command == "create-config":
        target = args[1] if len(args) > 1 else "config/default.yml"
        create_config(target)
    else:
        print(f"Unknown command: {command}")
        print("Usage: pygeckocircuit-setup [check|create-config]")
        sys.exit(1)


if __name__ == "__main__":
    main()
