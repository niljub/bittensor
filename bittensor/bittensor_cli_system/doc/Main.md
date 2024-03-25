# Bittensor CLI System Documentation

This documentation outlines the structure, usage, and extension guidelines for the Bittensor CLI (Command Line Interface) System. The system is designed to facilitate easy interaction with Bittensor networks through a command-line interface, offering both traditional CLI and interactive REPL modes.

## System Overview

The Bittensor CLI system comprises two main components:

1. **CLI Mode**: A standard command-line interface where commands are executed one at a time.
2. **REPL Mode**: An interactive Read-Eval-Print Loop mode that allows for a more dynamic interaction.

## Getting Started

### Launching the CLI

To start the CLI, use the following command:

```
btcli --interactive
```

Without the `--interactive` flag, the system defaults to the traditional CLI mode.

## CLI Mode

In CLI mode, commands are executed in the format:

```
btcli <command> [OPTIONS]
```

### Common Commands

- `connect`: Connects to a Bittensor network.
- `status`: Displays the current status of the Bittensor network connection.
- `exit`: Exits the CLI.

## REPL Mode

REPL mode provides an interactive shell for executing multiple commands in a session.

### Entering REPL Mode

Start REPL mode with the `--interactive` flag. Once in REPL mode, you can execute commands directly:

```
btcli --interactive
Welcome to Bittensor CLI. Type 'help' for a list of commands.
>> connect
Connected to Bittensor.
>> status
Currently connected to Bittensor.
```

### Exiting REPL Mode

To exit, type `exit`:

```
>> exit
Goodbye!
```

## Extending the CLI

### Creating Plugins

Plugins extend the functionality of the CLI. Each plugin should reside in its own directory with the suffix `_plugin`.

#### Structure

- **Directory**: `my_feature_plugin/`
- **Main File**: `my_feature_plugin/plugin.py`
- **Class Name**: Should reflect the functionality, e.g., `MyFeatureCLI`.

#### Plugin Configuration Class

For compatibility with legacy systems or to define specific configurations, include a `PluginNameConfig` class, e.g., `MyFeatureCLIConfig`.

### Naming Conventions

Follow the naming conventions outlined in the Plugin System Naming Convention Documentation to ensure consistency and clarity across the system.


