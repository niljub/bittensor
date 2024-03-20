import json
import os
import sys
import importlib
from typing import Any, Callable, Dict, Type


class SingletonMeta(type):
    """
    A metaclass for creating Singleton instances.
    """
    _instances: Dict[Type, "SingletonMeta"] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class CommandRegistry(metaclass=SingletonMeta):
    """
    A singleton registry for plugins in a CLI application, supporting configuration-driven lazy loading.
    This version correctly handles top-level commands, their subcommands, and aliases.
    """
    def __init__(self, commands: Dict[str, Any], plugin_path: str = "commands/") -> None:
        self._registry: Dict[str, Callable[[], Type]] = {}
        self._plugin_path = plugin_path
        sys.path.insert(0, self._plugin_path)
        self._load_plugins(commands)

    def _load_plugins(self, commands: Dict[str, Any]) -> None:
        """
        Prepares the commands, subcommands, and aliases for lazy loading based on the provided configuration.

        :param commands: Configuration dictionary for commands, subcommands, and aliases
        """
        for command_group, command_info in commands.items():
            module_base_path = command_info.get("module_base_path", "")
            for subcommand, class_name in command_info['commands'].items():
                full_command = f"{command_group} {subcommand}"
                self._prepare_command(full_command, module_base_path, class_name)

    def _prepare_command(self, full_command: str, module_base_path: str, class_name: str) -> None:
        """
        Prepares a command for lazy loading based on its full command path, module base path, and class name.

        :param full_command: Full command path including command group and subcommand
        :param module_base_path: The base path for the module where the command class is located
        :param class_name: Name of the class that implements the command
        """
        def loader() -> Type:
            module = importlib.import_module(f"{module_base_path}.{class_name}")
            return getattr(module, "run")

        self._registry[full_command] = loader

    def execute(self, full_command: str, console: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Executes the registered command, including command groups and subcommands, lazily importing the class.

        :param full_command: Full command path to execute
        :param console:
        :returns: Result of the executed command
        """
        if full_command not in self._registry:
            raise ValueError(f"Command '{full_command}' not registered.")

        command_class_loader = self._registry[full_command]
        command_class = command_class_loader()
        instance = command_class()
        return instance(console, *args, **kwargs)
