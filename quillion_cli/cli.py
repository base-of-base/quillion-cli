import os
import typing as t

import typer

from .commands.run import run_command
from .commands.new import new_command
from .debug.debugger import debugger


app = typer.Typer(help="Quillion CLI", pretty_exceptions_enable=False)


def version_callback(value: bool):
    if value:
        debugger.version()
        raise typer.Exit()


@app.callback()
def main(
    version: t.Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, help="Show version and exit"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Quiet mode - no debug output"
    ),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
    no_figlet: bool = typer.Option(False, "--no-figlet", help="Disable figlet banner"),
):
    """
    Quillion Command Line Interface
    """
    debugger.config.quiet = quiet or os.environ.get("QUILLION_QUIET", "0") == "1"
    debugger.config.no_color = (
        no_color or os.environ.get("QUILLION_NO_COLOR", "0") == "1"
    )
    debugger.config.no_figlet = (
        no_figlet or os.environ.get("QUILLION_NO_FIGLET", "0") == "1"
    )


app.command(name="run")(run_command)
app.command(name="new")(new_command)

if __name__ == "__main__":
    app()
