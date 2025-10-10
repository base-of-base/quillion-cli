import os
from datetime import datetime

import pyfiglet
import rich
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .. import __version__
from ..config.models import DebugConfig


class Debugger:
    def __init__(self, config: DebugConfig):
        self.config = config
        self.console = Console()

    def _should_log(self) -> bool:
        return not self.config.quiet

    def _format_message(self, symbol: str, message: str) -> str:
        timestamp = datetime.now().strftime("%H:%M:%S")
        if self.config.no_color:
            return f"{timestamp} │ {symbol} {message}"
        return f"[bold blue]{timestamp}[/] [dim]│[/] {symbol} {message}"

    def info(self, message: str):
        if self._should_log():
            self.console.print(self._format_message("", message))

    def success(self, message: str):
        if self._should_log():
            symbol = "✓" if self.config.no_color else "[green]✓[/]"
            self.console.print(self._format_message(symbol, message))

    def warning(self, message: str):
        if self._should_log():
            symbol = "⚠" if self.config.no_color else "[yellow]⚠[/]"
            self.console.print(self._format_message(symbol, message))

    def error(self, message: str):
        if self._should_log():
            symbol = "[red][/]"
            self.console.print(self._format_message(symbol, message))

    def version(self):
        if self._should_log():
            if self.config.no_color:
                self.console.print(f"Quillion CLI v{__version__}")
            else:
                self.console.print(
                    f"[bold green]Quillion CLI[/] v[cyan]{__version__}[/]"
                )

    def server_start(
        self, host: str, server_port: int, http_port: int, https: bool = False
    ):
        if not self._should_log():
            return

        protocol = "https" if https else "http"
        ws_protocol = "wss" if https else "ws"

        if self.config.no_color:
            self.console.print("\n" + "─" * os.get_terminal_size().columns)
            self.console.print("Quillion Dev Server")
            self.console.print("─" * os.get_terminal_size().columns)
            self.console.print("Server running!")
            self.console.print(f"Server:    {ws_protocol}://{host}:{server_port}")
            self.console.print(f"Frontend:  {protocol}://{host}:{http_port}")
            self.console.print("Press Ctrl+C to stop")
            self.console.print("─" * os.get_terminal_size().columns)
        else:
            panel = Panel(
                f"[bold green]Server running![/]\n\n"
                f"[bold]Server:[/]    [cyan]{ws_protocol}://{host}:{server_port}[/]\n"
                f"[bold]Frontend:[/]  [cyan]{protocol}://{host}:{http_port}[/]",
                box=rich.box.ROUNDED,
                style="blue",
                title="Quillion Dev Server",
                width=78,
            )
            self.console.print("\n" + "─" * os.get_terminal_size().columns)
            self.console.print(panel, justify="center")
            self.console.print("[dim]Press Ctrl+C to stop[/]\n")
            self.console.print("─" * os.get_terminal_size().columns)

    def http_server_start(self, host: str, port: int, https: bool = False):
        if not self._should_log():
            return

        protocol = "HTTPS" if https else "HTTP"
        if not self.config.no_color:
            self.console.print(f"{protocol} server started on {host}:{port}")
            self.console.print("Serving static files from packages directory")
        else:
            self.console.print(
                f"[green]✓[/] [bold]{protocol} server[/] started on [cyan]{host}:{port}[/]"
            )
            self.console.print("[dim]Serving static files from packages directory[/]")

    def banner(self):
        if self.config.quiet or self.config.no_figlet:
            return

        try:
            banner_text = pyfiglet.figlet_format("Q", font="slant")
        except:
            banner_text = "Q"

        if not self.config.no_color:
            text = Text(banner_text, style="bold magenta3")
            self.console.print("\n", justify="center")
            self.console.print(text, justify="center")
            self.console.print(
                Text(" Quillion Command Line Interface ", style="bold cyan"),
                justify="center",
            )
            self.console.print("\n", justify="center")


initial_config = DebugConfig(
    quiet=os.environ.get("QUILLION_QUIET", "0") == "1",
    no_color=os.environ.get("QUILLION_NO_COLOR", "0") == "1",
    no_figlet=os.environ.get("QUILLION_NO_FIGLET", "0") == "1",
)
debugger = Debugger(initial_config)
