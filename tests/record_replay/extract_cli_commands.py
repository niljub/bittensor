import json
import subprocess
from typing import Dict, Any


def execute_command(command: str) -> str:
    """
    Execute a shell command and return its output as a string.

    :param command: Command to be executed.
    :return: Output of the command.
    """
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command '{command}' failed: {result.stderr}")
    return result.stdout


def parse_help_output(help_output: str) -> Dict[str, Any]:
    """
    Parse the output of a help command to extract commands, subcommands, and options.

    :param help_output: Output of a help command.
    :return: Parsed commands, subcommands, and options.
    """
    lines = help_output.splitlines()
    parsed_data = {}
    current_section = None

    for line in lines:
        if line.startswith(' '):
            if current_section:
                parts = line.strip().split('  ', 1)
                if len(parts) == 2:
                    key, desc = parts
                    parsed_data[current_section][key.strip()] = desc.strip()
        else:
            section_title = line.strip(': ')
            if section_title:
                current_section = section_title
                parsed_data[current_section] = {}

    return parsed_data


def collect_cli_data(entrypoint: str) -> Dict[str, Any]:
    """
    Collect data about commands, subcommands, and options from the CLI tool.

    :param entrypoint: Entrypoint command of the CLI tool.
    :return: Collected CLI data.
    """
    cli_data = {"entrypoint": entrypoint, "commands": {}}

    # Get main help output
    main_help_output = execute_command(f"{entrypoint} -h")
    main_commands = parse_help_output(main_help_output)["Commands"]

    for command, description in main_commands.items():
        command_help_output = execute_command(f"{entrypoint} {command} -h")
        command_data = parse_help_output(command_help_output)

        subcommands = command_data.get("Subcommands", {})
        for subcommand, sub_desc in subcommands.items():
            subcommand_help_output = execute_command(f"{entrypoint} {command} {subcommand} -h")
            subcommand_data = parse_help_output(subcommand_help_output)

            subcommands[subcommand] = {
                "description": sub_desc,
                "options": subcommand_data.get("Options", {})
            }

        cli_data["commands"][command] = {
            "description": description,
            "subcommands": subcommands
        }

    return cli_data


def main():
    entrypoint = "btcli"
    cli_data = collect_cli_data(entrypoint)

    with open("btcli_commands.json", "w") as json_file:
        json.dump(cli_data, json_file, indent=4)


if __name__ == "__main__":
    main()
