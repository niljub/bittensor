import asyncio

from textual.reactive import *
from textual.widget import *
from textual.layouts import *
from textual_inputs import *
from textual.widgets import *
from textual.app import *
from textual.containers import *
from rich import *
from textual.screen import *


class CustomREPL(Widget):
    """A custom REPL widget for command input and execution."""

    def __init__(self, name: str = None):
        super().__init__()
        self.input = TextInput(name="repl_input", placeholder="btcli> ")

    async def on_mount(self) -> None:
        self.set_layout("horizontal")
        await self.layout.add(self.input)

    async def handle_key(self, event) -> None:
        if event.key == "enter":
            command = self.input.value
            # Process the command here
            self.input.value = ""  # Reset input after command processing





class DashboardScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Placeholder("Dashboard Screen")
        yield Footer()


class SettingsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Placeholder("Settings Screen")
        yield Footer()


class HelpScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Placeholder("Help Screen")
        yield Footer()


class Hello(Widget):
    """Display a greeting."""

    def render(self) -> RenderResult:
        return "Hello, [b]World[/b]!"


class RichLogApp(Widget):

    def __init__(self, name: str, id: str) -> None:
        super().__init__(name=name, id=id)
        self.messages = asyncio.LifoQueue()

    def compose(self) -> ComposeResult:
        yield RichLog(highlight=True, markup=True)

    async def on_mount(self) -> None:
        self.set_interval(0.5, self.refresh)  # Adjust as needed

    async def on_key(self, event: events.Key) -> None:
        """Write Key events to log."""
        text_log = self.query_one(RichLog)
        text_log.write(event)

    async def push_message(self, message: str) -> None:
        """Add a message to the log widget and update the display."""
        self.messages.put_nowait(message)
        self.refresh()

    async def update(self) -> None:
        """Update the log widget with new messages."""
        if self.messages:
            new_message = await self.messages.get()
            await self.update_content(new_message)

    async def update_content(self, message: str) -> None:
        """Append a message to the ScrollView content."""
        text_log = self.query_one(RichLog)
        text_log.write(message)

    async def on_ready(self) -> None:
        """Called  when the DOM is ready."""
        text_log = self.query_one(RichLog)

        text_log.write("test")
        text_log.write("[bold magenta]Write text or any Rich renderable!")


class Interactive(App):
    """Application with a custom layout including a status bar, tabbed display, user status bar, and REPL input prompt."""
    show_time = Reactive(datetime.now().strftime("%H:%M:%S"))

    CSS_PATH = "btcli_interactive.tcss"
    BINDINGS = [
        ("f", "toggle_files", "Toggle Files"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        with Static("One", classes="box", id="header"):
            yield Header(name="header status bar", show_clock=True, id="top-status-bar")

        with Static("Two", classes="box", id="main-display"):
            tabs = ("Main", "Errors", "Python")

            with TabbedContent(*tabs):

                yield RichLogApp(name="main", id="main-log")

                yield Static(id="code", expand=True)

                yield Static(id="code", expand=True)

        with Static("Three", classes="box", id="command-prompt"):
            yield CommandPrompt()

        yield Footer()

    async def on_load(self) -> None:
        """Load the app and widgets."""
        self.bind("escape", "quit")

    async def on_mount(self) -> None:
        """Mount widgets to the app."""
        self.input = Input(name="command_input", placeholder="Enter command here...")
        await self.dock(Footer(), edge="bottom")
        await self.view.dock(self.input, edge="bottom")

        # Focus on the input widget immediately
        self.set_focus(self.input)

    async def action_submit(self) -> None:
        """Handle the submission of the input."""
        command = self.input.value
        self.input.clear()

        # Handle the command
        print(f"Command entered: {command}")  # Replace this with actual command handling

        # Refocus on the input widget after command handling
        self.set_focus(self.input)

    async def on_key(self, event) -> None:
        """Intercept key presses."""
        if event.key == "enter":
            await self.action_submit()


    async def on_mount(self) -> None:
        await self.mount(CommandPrompt())




if __name__ == "__main__":
    app = Interactive()
    app.run()
