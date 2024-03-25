from abc import ABC, abstractmethod
import os
import importlib.util
from typing import Type, Dict, Any

from bittensor.bittensor_plugin_system.core.base_plugin import BasePlugin
import logging


class CLIPlugin(BasePlugin):
    """
    Abstract base class for CLI plugins.
    """
    def __init__(self):
        super().__init__()

    @abstractmethod
    def initialize(self, config_path: str) -> None:
        """
        Method to initialize the plugin. This should include any setup necessary for the plugin to function.
        """
        pass

    @abstractmethod
    def execute(self, command: str, *args: Any, **kwargs: Any) -> None:
        """
        Executes a command within the context of the plugin.

        Args:
            command (str): The command to execute.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        pass

    @abstractmethod
    def _core_execute(self, data: Any) -> Any:
        """
        The core execution method that needs to be implemented by the subclass.

        Args:
            data (Any): Input data for the plugin to process.

        Returns:
            Any: The result of processing the input data.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Cleans up any resources used by the plugin.
        """
        pass


class TransportPlugin(BasePlugin):
    """
    Abstract base class for Transport plugins.
    """

    @abstractmethod
    def initialize(self, config_path: str) -> None:
        """
        Method to initialize the plugin. This should include any setup necessary for the plugin to function.
        """
        pass

    @abstractmethod
    def execute(self, command: str, *args: Any, **kwargs: Any) -> None:
        """
        Executes a command within the context of the plugin.

        Args:
            command (str): The command to execute.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        pass

    @abstractmethod
    def _core_execute(self, data: Any) -> Any:
        """
        The core execution method that needs to be implemented by the subclass.

        Args:
            data (Any): Input data for the plugin to process.

        Returns:
            Any: The result of processing the input data.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Cleans up any resources used by the plugin.
        """
        pass
