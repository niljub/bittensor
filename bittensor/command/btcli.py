import typer
from typing import Optional

app = typer.Typer()


@app.command()
async def greet(name: str, formal: Optional[bool] = False):
    greeting = "Hello"
    if formal:
        greeting = f"{greeting}, Mr. {name}"
    else:
        greeting = f"{greeting} {name}"
    await some_async_operation(greeting)


async def some_async_operation(message: str):
    # Simulate an async operation, e.g., database call
    print(message)