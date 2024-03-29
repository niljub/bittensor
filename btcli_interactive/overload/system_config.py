import os
import argparse
from typing import *
import yaml


class InvalidConfigFile(Exception):
    """In place of YAMLError"""

    pass


class ImmutableDotDict(dict):
    """
    An extension of the dictionary that supports dot notation and can be made immutable.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__locked = False

    def __getattr__(self, item):
        value = self.get(item)
        if isinstance(value, dict) and not isinstance(value, ImmutableDotDict):
            value = ImmutableDotDict.from_dict(value)
            self[item] = value  # Update with wrapped value
        return value

    def __setattr__(self, key, value):
        if key == "_ImmutableDotDict__locked":
            super().__setattr__(key, value)
        elif self.__locked:
            raise AttributeError("This ImmutableDotDict is locked and cannot be modified.")
        else:
            super().__setattr__(key, value)

    def __setitem__(self, key, value):
        if self.__locked:
            raise KeyError("This ImmutableDotDict is locked and cannot be modified.")
        super().__setitem__(key, value)

    def __delattr__(self, item):
        if self.__locked:
            raise AttributeError("This ImmutableDotDict is locked and cannot be deleted.")
        super().__delattr__(item)

    def __delitem__(self, key):
        if self.__locked:
            raise KeyError("This ImmutableDotDict is locked and cannot be deleted.")
        super().__delitem__(key)

    def unlock(self):
        if self.__locked:
            self.__locked = False

    def unlock_and_update(self, data: Dict[str, Any]) -> None:
        """Unlocks the current object, updates it with new data, and re-locks it if it was originally locked.

        Args:
            data (Dict[str, Any]): The data to update the object with.
        """
        was_locked = self.__locked
        if was_locked:
            self.unlock()

        for key, value in self.__dict__.items():
            if key.startswith("_YourClass__"):  # Adjust based on your class name
                attr_key = key[11:]  # Removing the private name mangling prefix
                if attr_key in data:
                    setattr(self, attr_key, data[attr_key])
                    continue
            if isinstance(value, ImmutableDotDict):
                v_was_locked = getattr(value, "_ImmutableDotDict__locked", False)
                if v_was_locked:
                    value.unlock()
                if key in data:  # Using key to match with data for updating
                    setattr(self, key, data[key])
                if v_was_locked:
                    value.lock()

        if was_locked:
            self.lock()

    @staticmethod
    def from_dict(data):
        """
        Recursively converts a dictionary to an ImmutableDotDict, including all nested dictionaries.

        Args:
            data: The dictionary to convert.

        Returns:
            An ImmutableDotDict object with the same keys and values.
        """
        if not isinstance(data, dict):
            return data
        else:
            return ImmutableDotDict({key: ImmutableDotDict.from_dict(value) for key, value in data.items()})

    def merge(self, b):
        """
        Merges the current config with another config.

        Args:
            b: Another config to merge.
        """
        if not self.__locked:
            super().self = self._merge(self, b)

    @classmethod
    def merge_all(cls, configs: List["config"]) -> "ImmutableDotDict":
        """
        Merge all configs in the list into one config.
        If there is a conflict, the value from the last configuration in the list will take precedence.

        Args:
            configs (list of config):
                List of configs to be merged.

        Returns:
            config:
                Merged config object.
        """
        result = cls()
        for cfg in configs:
            result.merge(cfg)
        return result

    def is_set(self, param_name: str) -> bool:
        """
        Returns a boolean indicating whether the parameter has been set or is still the default.
        """
        if param_name not in self.get("__is_set"):
            return False
        else:
            return self.get("__is_set")[param_name]

    def lock(self):
        """
        Locks the ImmutableDotDict, preventing any further modifications.
        """
        for value in self.values():
            if isinstance(value, ImmutableDotDict):
                value.lock()
        self.__locked = True


class SystemConfig:
    """
    Handles the system configuration by prioritizing command line arguments, environment
    variables, config files, hardcoded defaults, and making the configuration immutable
    once fully loaded.

    Supports loading and overriding configurations from multiple sources with the
    following priority: hardcoded defaults < config files < environment variables
    < command line arguments.

    Additionally, supports backwards compatibility with legacy config.py files in plugins.
    """

    def __init__(self, defaults: Dict[str, Any], config_file_path: str, environment_prefix: str) -> None:
        """
        Initializes the SystemConfig with hardcoded defaults, a path to the main config file,
        and a prefix for environment variables.

        Args:
            defaults (Dict[str, Any]): Hardcoded default configurations.
            config_file_path (str): Path to the main YAML configuration file.
            environment_prefix (str): Prefix for relevant environment variables.
        """
        self.config = ImmutableDotDict.from_dict(defaults)
        self.config_file_path = config_file_path
        self.environment_prefix = environment_prefix

        self._load_config_file()
        self._load_environment_variables()
        self._load_command_line_arguments()
        self._finalize_config()

    def _load_config_file(self) -> None:
        """
        Loads configuration from a YAML file, overriding hardcoded defaults.
        """
        if os.path.exists(self.config_file_path):
            with open(self.config_file_path, "r") as file:
                file_config = yaml.safe_load(file)
                self._update_config(file_config)

    def _load_environment_variables(self) -> None:
        """
        Loads configuration from environment variables, overriding previous configurations.
        """
        for key in os.environ:
            if key.startswith(self.environment_prefix):
                config_key = key[len(self.environment_prefix):].lower()
                self.config[config_key] = os.environ[key]

    def _load_command_line_arguments(self) -> None:
        """
        Loads configuration from command line arguments, overriding previous configurations.
        """
        parser = argparse.ArgumentParser()
        for key in self.config.keys():
            parser.add_argument(f"--{key}", dest=key)
        args = parser.parse_args()
        args_dict = vars(args)
        for key, value in args_dict.items():
            if value is not None:
                self.config[key] = value

    def _finalize_config(self):
        """
        Finalizes the configuration, making it immutable.
        """
        self.config.lock()

    def _update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Updates the current configuration with new values from a dictionary.

        Args:
            new_config (Dict[str, Any]): New configuration values to update.
        """
        self.config.unlock_and_update(new_config)

