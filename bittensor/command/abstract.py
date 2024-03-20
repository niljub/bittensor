from abc import ABC, abstractmethod
from typing import Any


class AbstractBaseCommand(ABC):
    """
    Abstract base class for defining commands.
    """

    @staticmethod
    @abstractmethod
    def describe(console: Any) -> None:
        """
        Describe the command and its arguments

        Parameters:
            console: The console context for executing the command.
        """
        pass


    @staticmethod
    @abstractmethod
    def run(console: Any) -> None:
        """
        Execute the command with the given CLI context.

        Parameters:
            console: The console context for executing the command.
        """
        pass

    @staticmethod
    @abstractmethod
    def check_config(config: Any) -> None:
        """
        Check if the necessary configuration is set for the command.

        Parameters:
            config: The configuration to check.
        """
        pass

    @staticmethod
    @abstractmethod
    def add_args(parser: Any) -> None:
        """
        Add command-specific arguments to the parser.

        Parameters:
            parser: The argument parser to add arguments to.
        """
        pass
