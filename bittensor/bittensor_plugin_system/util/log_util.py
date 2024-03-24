import logging
import os


def setup_plugin_logger(name: str, log_path: str = "logs") -> logging.Logger:
    """
    Sets up a logger for a plugin, storing logs in a file named after the plugin.

    Args:
        name (str): The name of the plugin.
        log_path (str): The directory where log files will be stored. Defaults to "logs".

    Returns:
        logging.Logger: The logger configured for the plugin.
    """
    if not os.path.exists(log_path):
        os.makedirs(log_path)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    return logger
