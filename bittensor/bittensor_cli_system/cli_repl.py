# cli_repl.py
from datetime import datetime
import sys
import asyncio
from injector import inject
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel


class CLIRepl:
    """
    Implements the CLI REPL user interface for the Bittensor CLI system.
    """

    @inject
    def __init__(self, console: Console, layout: Layout):
        self.console = console
        self.layout = layout
        self.current_mode = "default"
        self.setup_layout()

    def setup_layout(self):
        """
        Initializes the layout for the CLI REPL interface.
        """
        self.layout.split(
            Layout(name="main_status", size=3),
            Layout(name="display", ratio=1),
            Layout(name="user_status", size=3),
            Layout(name="input", size=1),
        )
        self.update_main_status("Disconnected")
        self.update_display(
            "Welcome to Bittensor CLI. Type 'help' for a list of commands."
        )
        self.update_user_status("")

    async def update_main_status(self, status: str):
        """
        Updates the main status bar at the top of the screen.

        Args:
            status (str): The status message to display.
        """
        self.layout["main_status"].update(
            Panel(f"[bold magenta]BITTENSOR[/bold magenta] - {status}", style="on blue")
        )

    async def update_display(self, content: str):
        """
        Updates the display panel with the provided content.

        Args:
            content (str): The content to display.
        """
        self.layout["display"].update(Panel(content, border_style="green"))

    async def update_user_status(self, status: str):
        """
        Updates the user status bar with the provided status message.

        Args:
            status (str): The status message to display.
        """
        clock = datetime.now().strftime("%H:%M:%S")
        mode_display = f"Mode: {self.current_mode.capitalize()}"
        self.layout["user_status"].update(
            Panel(f"{clock} | {mode_display} | {status}", style="on blue")
        )

        async def print_counter():
            """
            Coroutine that prints counters.
            """
            try:
                i = 0
                while True:
                    print("Counter: %i" % i)
                    i += 1
                    await asyncio.sleep(3)
            except asyncio.CancelledError:
                print("Background task cancelled.")

        async def interactive_shell():
            """
            Like `interactive_shell`, but doing things manual.
            """
            # Create Prompt.
            session = PromptSession("Say something: ")

            # Run echo loop. Read text from stdin, and reply it back.
            while True:
                try:
                    result = await session.prompt_async()
                    print(f'You said: "{result}"')
                except (EOFError, KeyboardInterrupt):
                    return

        async def main():
            with patch_stdout():
                background_task = asyncio.create_task(print_counter())
                try:
                    await interactive_shell()
                finally:
                    background_task.cancel()
                print("Quitting event loop. Bye.")

    async def start(self):
        """
        Starts the REPL, continuously accepting input commands from the user.
        """
        self.setup_layout()
        #with self.console.status("Bittensor CLI is running...", spinner="dots"):
        self.console.print(self.layout)
        while True:
            user_input = self.console.input("[bold green]Bittensor > [/bold green]")
            await self.process_command(user_input)

    async def process_command(self, command: str):
        """
        Processes the entered command and updates the REPL accordingly.

        Args:
            command (str): The command entered by the user.
        """
        # Example command processing
        if command == "exit":
            self.console.print("Exiting Bittensor CLI...", style="bold red")
            sys.exit(0)
        elif command == "help":
            await self.update_display("Help: List of commands...")
        else:
            await self.update_display(f"Command '{command}' not recognized.")
