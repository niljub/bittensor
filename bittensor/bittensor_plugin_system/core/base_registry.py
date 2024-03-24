import os
import importlib.util
from typing import Type, Dict, Generic, TypeVar
from abc import ABC, abstractmethod
from base_plugin import BasePlugin
import logging

T = TypeVar("T", bound=BasePlugin)


class BasePluginRegistry(ABC, Generic[T]):
    """
    Abstract base class for managing the registration, deregistration,
    and execution of plugins, supporting dynamic updates and lazy loading
    of plugin functionalities.
    """

    def __init__(self) -> None:
        """Initialize the PluginRegistry with empty registries and a logger."""
        self._plugins: Dict[str, Type[T]] = {}
        self._plugin_instances: Dict[str, T] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def discover_plugins(self, directory: str = "plugins") -> None:
        """
        Automatically discovers and registers plugins located in the specified directory.

        Args:
            directory (str): The directory to search for plugins. Defaults to "plugins".
        """
        raise NotImplementedError

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

    @abstractmethod
    def execute_plugin(self, plugin_name: str, data: any) -> any:
        """
        Executes a registered plugin's functionality, lazily initializing the plugin if necessary.

        Args:
            plugin_name (str): The name of the plugin to execute.
            data (any): The input data for the plugin's execute method.

        Returns:
            any: The result from the plugin's execution, or None if the plugin cannot be executed.
        """
        raise NotImplementedError
