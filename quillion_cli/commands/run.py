import time
import typing as t

import typer
from pathlib import Path

from ..config.loader import load_config
from ..debug.debugger import debugger
from ..server.http_server import start_http_server
from ..server.websocket_server import run_server, restart_server, shutdown_server
from ..utils.file_watcher import setup_file_watchers, shutdown_watchers


def start_development_server(config, project_dir: str, hot_reload: bool = True):
    """Start development server with optional hot reload"""
    process = run_server(config, project_dir)
    if process is None:
        return

    httpd, http_thread = start_http_server(config, project_dir)

    debugger.server_start(
        config.server.host,
        config.server.port,  # WebSocket server port
        config.http_server.port,  # HTTP server port
    )

    if not hot_reload:
        try:
            process.wait()
        except KeyboardInterrupt:
            debugger.info("Shutting down server...")
            process.terminate()
        return

    def restart_callback():
        nonlocal process
        process = restart_server(config, project_dir, process)

    observers = setup_file_watchers(config, project_dir, restart_callback)

    try:
        while True:
            time.sleep(0.5)
            if process and process.poll() is not None:
                debugger.error("Server process died, restarting...")
                process = restart_server(config, project_dir, process)
    except KeyboardInterrupt:
        debugger.info("Shutting down servers...")
        shutdown_servers(process, httpd, observers)


def shutdown_servers(process: t.Optional, httpd: t.Optional, observers: t.List):
    """Cleanup all server processes and watchers"""
    shutdown_server(process)

    if httpd:
        httpd.shutdown()

    shutdown_watchers(observers)


def run_command(
    name: t.Optional[str] = typer.Argument(
        None, help="Project name or directory to run"
    ),
    hot_reload: bool = typer.Option(
        True,
        "--hot-reload/--no-hot-reload",
        help="Enable/disable hot reload functionality",
    ),
    port: t.Optional[int] = typer.Option(
        None, "--port", "-p", help="Override server port from config"
    ),
    host: t.Optional[str] = typer.Option(
        None, "--host", help="Override server host from config"
    ),
    http_port: t.Optional[int] = typer.Option(
        None, "--http-port", help="Override HTTP server port from config"
    ),
    no_http: bool = typer.Option(
        False, "--no-http", help="Disable HTTP server for static files"
    ),
    verbose_http: bool = typer.Option(
        False, "--verbose-http", help="Enable HTTP server logging"
    ),
):
    """Run Quillion development server with hot reload"""
    debugger.banner()

    project_dir = Path(name).resolve() if name else Path.cwd()

    if not project_dir.exists():
        debugger.error(f"Project directory not found: {project_dir}")
        raise typer.Exit(1)

    config = load_config(str(project_dir))

    if port is not None:
        config.server.port = port
        debugger.info(f"Port overridden to: {port}")
    if host is not None:
        config.server.host = host
        debugger.info(f"Host overridden to: {host}")
    if http_port is not None:
        config.http_server.port = http_port
        debugger.info(f"HTTP port overridden to: {http_port}")
    if no_http:
        config.http_server.enabled = False
        debugger.info("HTTP server disabled")
    if verbose_http:
        config.http_server.silent = False
        debugger.info("HTTP server logging enabled")

    start_development_server(config, str(project_dir), hot_reload)
