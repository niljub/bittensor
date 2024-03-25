import os
from typing import Any
import argparse

from bittensor.config import DefaultConfig
from bittensor.bittensor_plugin_system.core.cli_plugin import CLIPlugin


class AxonPlugin(CLIPlugin):
    def execute(self, command: str, *args: Any, **kwargs: Any) -> None:
        pass

    def _core_execute(self, data: Any) -> Any:
        pass

    def shutdown(self) -> None:
        pass

    def initialize(self, config_path: str) -> None:
        pass
