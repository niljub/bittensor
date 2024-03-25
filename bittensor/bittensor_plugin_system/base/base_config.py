from abc import ABC, abstractmethod
import argparse
from typing import Optional
import os


class BaseConfig(ABC):
    """
    Abstract base class for plugin configuration. This class defines the structure for
    configuration management, including parsing command-line arguments and printing help.
    """

    @classmethod
    @abstractmethod
    def config(cls):
        """
        Abstract method for parsing command-line arguments to form a configuration object.
        """
        pass

    @classmethod
    @abstractmethod
    def help(cls):
        """
        Abstract method for printing the help text (list of command-line arguments and
        their descriptions) to stdout.
        """
        pass

    @classmethod
    @abstractmethod
    def add_args(cls, parser: argparse.ArgumentParser, prefix: Optional[str] = None):
        """
        Abstract method for adding command-line arguments to the argument parser.

        Args:
            parser (argparse.ArgumentParser): Argument parser to which the arguments will be added.
            prefix (Optional[str]): Prefix to add to the argument names. Defaults to None.
        """
        pass
