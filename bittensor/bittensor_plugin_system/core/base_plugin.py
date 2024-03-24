from abc import ABC, abstractmethod
from typing import Any, Dict
import yaml
import logging


class BasePlugin(ABC):
    """
    An abstract base class that defines a common interface for all plugins,
    including lifecycle methods and utility functions.
    """

    def __init__(self) -> None:
        """Initializes the plugin."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = {}

    @abstractmethod
    def initialize(self, config_path: str) -> None:
        """
        Initializes the plugin with configuration from a YAML file.

        Args:
            config_path (str): The path to the configuration YAML file.
        """
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        self.logger.info("Plugin initialized with configuration from %s", config_path)

    @abstractmethod
    def execute(self, data: Any) -> Any:
        """
        Executes the plugin's main functionality.

        Args:
            data (Any): Input data for the plugin to process.

        Returns:
            Any: The result of processing the input data.
        """
        self.before_execute(data)
        result = self._core_execute(data)
        self.after_execute(data, result)
        return result

    @abstractmethod
    def shutdown(self) -> None:
        """Shuts down the plugin, releasing any resources if necessary."""
        self.logger.info("Plugin shutdown.")

    def before_execute(self, data: Any) -> None:
        """
        Hook method called before execute().

        Args:
            data (Any): The input data for the execution.
        """
        self.logger.debug("Executing before_execute hook.")

    def after_execute(self, data: Any, result: Any) -> None:
        """
        Hook method called after execute().

        Args:
            data (Any): The input data for the execution.
            result (Any): The result of the execution.
        """
        self.logger.debug("Executing after_execute hook.")

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
