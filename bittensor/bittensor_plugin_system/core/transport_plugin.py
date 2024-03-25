from abc import ABC, abstractmethod
import argparse
import importlib.util
import os
import logging
from typing import Type, Dict, TypeVar, Generic, Optional, Any

from bittensor.bittensor_plugin_system.base import (
    BasePlugin,
    BaseConfig,
    BasePluginRegistry,
)

T = TypeVar("T", bound=BasePlugin)


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


class TransportPluginRegistry(BasePluginRegistry, Generic[T]):
    """
    Manages the registration, deregistration, and execution of Transport plugins, supporting
    dynamic updates and fast loading of plugin functionalities.
    """

    def __init__(self) -> None:
        """Initialize the CLIPluginRegistry with empty registries and a logger."""
        super().__init__()
        self._plugins: Dict[str, Type[T]] = {}
        self._plugin_instances: Dict[str, T] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def discover_plugins(self, directory: str = "plugins") -> None:
        """
        Automatically discovers and registers plugins located in the specified directory.

        Args:
            directory (str): The directory to search for plugins. Defaults to "plugins".
        """
        for filename in os.listdir(directory):
            if not filename.endswith(".py") or filename.startswith("__"):
                continue
            module_name = filename[:-3]
            module_path = os.path.join(directory, filename)
            self._register_plugin(module_name, module_path)

    def _register_plugin(self, module_name: str, module_path: str) -> None:
        """
        Registers a plugin by importing it and adding it to the plugins registry.

        Args:
            module_name (str): The name of the module.
            module_path (str): The filesystem path to the module.
        """
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if (
                    isinstance(attribute, type)
                    and issubclass(attribute, BasePlugin)
                    and attribute is not BasePlugin
                ):
                    self._plugins[module_name] = attribute
                    self.logger.info(f"Registered plugin: {module_name}")

    def deregister_plugin(self, plugin_name: str) -> None:
        """
        Deregisters a plugin, removing it from the registry.

        Args:
            plugin_name (str): The name of the plugin to deregister.
        """
        if plugin_name in self._plugins:
            del self._plugins[plugin_name]
            self.logger.info(f"Deregistered plugin: {plugin_name}")
        if plugin_name in self._plugin_instances:
            del self._plugin_instances[plugin_name]
            self.logger.info(f"Removed plugin instance: {plugin_name}")

    def execute_plugin(self, plugin_name: str, data: any) -> any:
        """
        Executes a registered plugin's functionality, lazily initializing the plugin if necessary.

        Args:
            plugin_name (str): The name of the plugin to execute.
            data (any): The input data for the plugin's execute method.

        Returns:
            any: The result from the plugin's execution, or None if the plugin cannot be executed.
        """
        plugin = self._plugin_instances.get(plugin_name)
        if not plugin and plugin_name in self._plugins:
            plugin_class = self._plugins[plugin_name]
            plugin = plugin_class()
            self._plugin_instances[plugin_name] = plugin
            plugin.initialize(config_path=f"{plugin_name}_config.yaml")

        if plugin:
            try:
                return plugin.execute(data)
            except Exception as e:
                self.logger.error(
                    f"Error executing plugin {plugin_name}: {e}", exc_info=True
                )
        else:
            self.logger.error(f"Plugin {plugin_name} is not registered.")
            return None


class TransportConfig(BaseConfig):
    """
    Transport Plugin Configuration class for parsing transport-specific command-line arguments.
    """

    @classmethod
    def config(cls):
        parser = argparse.ArgumentParser()
        cls.add_args(parser)
        args = parser.parse_args()
        return args

    @classmethod
    def help(cls):
        parser = argparse.ArgumentParser()
        cls.add_args(parser)
        parser.print_help()

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser, prefix: Optional[str] = None):
        # Implement transport-specific argument addition here
        prefix_str = "" if prefix is None else prefix + "."
        # Here you'd add transport-specific command-line arguments to the parser
        pass
