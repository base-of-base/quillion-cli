import contextlib
import os
import subprocess
import sys
import typing as t
from pathlib import Path

from ..debug.debugger import debugger


def run_server(config, project_dir: str) -> t.Optional[subprocess.Popen]:
    """Start the main server process"""
    server_cfg = config.server
    assets_cfg = config.assets
    entry_point = Path(project_dir) / server_cfg.entry_point

    if not entry_point.exists():
        debugger.error(f"Entry point not found: {entry_point}")
        return None

    env = os.environ.copy()
    env.update(
        {
            "QUILLION_HOST": server_cfg.host,
            "QUILLION_PORT": str(server_cfg.port),
            "QUILLION_QUIET": "1" if debugger.config.quiet else "0",
            "QUILLION_NO_COLOR": "1" if debugger.config.no_color else "0",
            "QUILLION_NO_FIGLET": "1" if debugger.config.no_figlet else "0",
            "QUILLION_ASSET_HOST": assets_cfg.host,
            "QUILLION_ASSET_PORT": str(assets_cfg.port),
            "QUILLION_ASSET_PATH": assets_cfg.path,
        }
    )

    cmd = [sys.executable, str(entry_point)]

    try:
        return subprocess.Popen(cmd, cwd=project_dir, env=env)
    except Exception as e:
        debugger.error(f"Cannot run server: {e}")
        return None


def restart_server(
    config, project_dir: str, process: subprocess.Popen
) -> t.Optional[subprocess.Popen]:
    """Restart the server process"""
    if process:
        with contextlib.suppress(Exception):
            process.terminate()
            process.wait(timeout=5)
        with contextlib.suppress(Exception):
            process.kill()

    return run_server(config, project_dir)


def shutdown_server(process: t.Optional[subprocess.Popen]):
    """Cleanup server process"""
    if process:
        with contextlib.suppress(Exception):
            process.terminate()
            process.wait(timeout=3)
        with contextlib.suppress(Exception):
            process.kill()
