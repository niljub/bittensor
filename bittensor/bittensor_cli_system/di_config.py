# di_config.py

from injector import Module, provider, singleton
from rich.console import Console
from rich.layout import Layout
from bittensor.bittensor_cli_system.cli_util import Display


class DIModule(Module):
    @singleton
    @provider
    def provide_console(self) -> Console:
        return Console()

    @singleton
    @provider
    def provide_display(self, console: Console) -> Display:
        return Display(console)

    @singleton
    @provider
    def provide_layout(self) -> Layout:
        # Here you can configure your layout as needed before returning it
        return Layout()
