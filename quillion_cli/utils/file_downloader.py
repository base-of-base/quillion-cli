from pathlib import Path
from typing import List, Optional
import requests
import typer
from rich.progress import (
    Progress,
    BarColumn,
    DownloadColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
    SpinnerColumn,
)
from rich.console import Console
from rich.panel import Panel
from rich import box

from ..debug.debugger import debugger

ASSETS = [
    "package.json",
    "quillion.d.ts",
    "quillion.js",
    "quillion_bg.wasm",
    "quillion_bg.wasm.d.ts",
]
REPO_URL = "https://api.github.com/repos/base-of-base/quillion-core/releases/latest"


def get_release_assets() -> Optional[List[dict]]:
    response = requests.get(REPO_URL, timeout=30)
    response.raise_for_status()
    release_data = response.json()
    return release_data.get("assets", [])


def downloads_assets(project_dir: Path):
    console = Console()

    assets = get_release_assets()
    if not assets:
        debugger.error("No assets found in the release")
        raise typer.Exit(1)

    q_dir = project_dir / ".q"
    q_dir.mkdir(exist_ok=True)
    pkg_dir = q_dir / "pkg"
    pkg_dir.mkdir(exist_ok=True)

    with Progress(
        BarColumn(bar_width=50, complete_style="green"),
        TextColumn("[progress.description]{task.description}"),
        "•",
        "[progress.percentage]{task.percentage:>3.0f}%",
        transient=True,
        console=console,
    ) as progress:

        main_task = progress.add_task("Downloading internal assets", total=len(ASSETS))

        for asset in assets:
            asset_name = asset["name"]
            if asset_name in ASSETS:
                download_url = asset["browser_download_url"]
                destination = pkg_dir / asset_name

                response = requests.get(download_url, timeout=30)
                response.raise_for_status()

                with open(destination, "wb") as f:
                    f.write(response.content)

                progress.update(main_task, advance=1)
