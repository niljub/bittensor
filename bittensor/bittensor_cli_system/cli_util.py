# util/display_util.py

from rich.console import Console
from injector import inject, singleton


@singleton
class Display:
    @inject
    def __init__(self, console: Console):
        self._console = console

    def display(self, message: str) -> None:
        """
        Displays a message to the console.

        Args:
            message (str): The message to display.
        """
        self._console.print(message)
