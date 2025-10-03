import typing as t
import typer
from pathlib import Path

from quillion_cli.utils.file_downloader import downloads_assets

from ..debug.debugger import debugger
from ..utils.templates import process_templates


def new_command(
    name: t.Optional[str] = typer.Argument(None, help="New project name"),
    port: int = typer.Option(1337, "--port", "-p", help="Default server port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Default server host"),
    http_port: int = typer.Option(8000, "--http-port", help="Default HTTP server port"),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        "-y",
        help="Run in non-interactive mode (auto-confirm all prompts)",
    ),
):
    """Create new Quillion project"""
    debugger.banner()

    if name is None:
        debugger.error("Project name is required")
        raise typer.Exit(1)

    project_dir = Path(name).resolve()
    project_dir.mkdir(exist_ok=True)

    config_path = project_dir / "quillion.toml"

    if config_path.exists():
        debugger.warning("quillion.toml already exists in this directory")
        if not non_interactive:
            if not typer.confirm("Overwrite existing config?"):
                return

    context = {
        "project_name": name,
        "port": port,
        "host": host,
        "http_port": http_port,
        "websocket_address": f"ws://{host}:{port}",
        "app_name": name.capitalize(),
    }

    templates_dir = Path(__file__).parent.parent / ".templates"

    if not templates_dir.exists():
        debugger.error(f"Templates directory not found: {templates_dir}")
        raise typer.Exit(1)

    process_templates(str(project_dir), context, templates_dir)

    debugger.success(f"Project '{name}' created in {project_dir}")
    debugger.info(f"Run with: q run {name}")
