# CLI Entrypoint
# cli.py

import typer
from injector import Injector
from bittensor.bittensor_cli_system.di_config import DIModule
from bittensor.bittensor_cli_system.cli_repl import CLIRepl  # This should be your implementation of the REPL interface
from bittensor.bittensor_cli_system.cli_util import Display


app = typer.Typer()


def main(interactive: bool = typer.Option(False, "--interactive", "-i", help="Enter interactive CLI REPL mode")):
    """
    Main entry point for the Bittensor CLI.

    Args:
        interactive (bool): If True, enters interactive CLI REPL mode. Defaults to False.
    """
    injector = Injector([DIModule()])
    if interactive:
        repl = injector.get(CLIRepl)
        repl.start()
    else:
        display = injector.get(Display)
        display.display("Non-interactive mode not yet implemented.")


if __name__ == "__main__":
    app.command()(main)()

