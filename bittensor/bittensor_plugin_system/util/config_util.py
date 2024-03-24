import yaml
from typing import Any, Dict


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Loads a YAML configuration file and returns its contents as a dictionary.

    Args:
        config_path (str): The path to the YAML configuration file.

    Returns:
        Dict[str, Any]: The configuration settings and values.
    """
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)
