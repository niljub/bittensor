# Standard Library
import argparse
import os
import yaml
import flatdict

# 3rd Party
from rich.prompt import Prompt
from rich.table import Table

# Bittensor
import bittensor

# Local
from . import defaults

class ProfileCreateCommand:
    """
    Executes the ``create`` command.

    This class provides functionality to create a profile by prompting the user to enter various attributes.
    The entered attributes are then written to a profile file.

    """

    @staticmethod
    def run(cli):
        ProfileCreateCommand._run(cli)   

    @staticmethod
    def _run(cli: "bittensor.cli"):
        ProfileCreateCommand._write_profile(cli.config)

    @staticmethod
    def _write_profile(config: "bittensor.config"):
        path = os.path.expanduser(config.profile.path)
        profile_name = config.profile.name
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            bittensor.__console__.print(
                f":cross_mark: [red]Failed to create directory for profile[/red]:[bold white] {e}"
            )
            return
        
        if os.path.exists(f"{path}{profile_name}") and not config.no_prompt:
            overwrite = None
            while overwrite not in ["y", "n"]:
                overwrite = Prompt.ask(f"Profile {profile_name} already exists. Overwrite?")
                if overwrite:
                    overwrite = overwrite.lower()
            if overwrite == "n":
                bittensor.__console__.print(
                    ":cross_mark: [red]Failed to write profile[/red]:[bold white] User denied."
                    )
                return
            
        try:
            with open(f"{path}/btcli-{profile_name}.yaml", "w+") as f:
                f.write(yaml.dump(config))
        except Exception as e:
            bittensor.__console__.print(
                f":cross_mark: [red]Failed to write profile[/red]:[bold white] {e}"
            )
            return
        
        bittensor.__console__.print(
            f":white_check_mark: [bold green]Profile {profile_name} written to {path}[/bold green]"
        )

    @staticmethod
    def check_config(config: "bittensor.config"):
        return config is not None

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        list_parser = parser.add_parser("create", help="""Create profile""")
        list_parser.set_defaults(func=ProfileCreateCommand.run)
        list_parser.add_argument(
            "--profile.name",
            type=str,
            default=defaults.profile.name,
            help="The name of the profile",
        )
        list_parser.add_argument(
            "--profile.path",
            type=str,
            default=defaults.profile.path,
            help="The path to the profile directory",
        )
        bittensor.subtensor.add_args(list_parser)
        bittensor.wallet.add_args(list_parser)

class ProfileListCommand:
    """
    Executes the ``list`` command.

    This class provides functionality to list all profiles in the profile directory.

    """

    @staticmethod
    def run(cli):
        ProfileListCommand._run(cli)

    @staticmethod
    def _run(cli: "bittensor.cli"):
        profile_path = os.path.expanduser(cli.config.profile.path)
        profile_details = ProfileListCommand.get_profile_details(profile_path)
        
        ProfileListCommand.print_profile_details(cli, profile_path, profile_details)
    
    @staticmethod
    def get_profile_details(profile_path):
        if not os.path.isdir(profile_path):
            bittensor.__console__.print(f"[red]profile.path is not a directory:[/red][bold white] {profile_path}")
            return
        
        try:
            files = os.listdir(profile_path)
            profile_details = []
            for filename in files:
                if filename.startswith('btcli-') and filename.endswith('.yaml'):
                    # Extract the string between 'btcli-' and '.yaml'
                    profile_name = filename[len('btcli-'):-len('.yaml')]
                    # Get the full file path
                    full_path = os.path.join(profile_path, filename)
                    # Get the file size
                    file_size = os.path.getsize(full_path)
                    # Append the details as a tuple to the list
                    profile_details.append((profile_name, full_path, f"{file_size} bytes"))
            return profile_details
        except Exception as e:
            bittensor.__console__.print(
                f"[red]Failed to list profiles[/red]:[bold white] {e}"
            )
            return
    
    @staticmethod
    def print_profile_details(cli, profile_path, profile_details):
        if not profile_details:
            bittensor.__console__.print(
                f":cross_mark: [red]No profiles found in '{profile_path}'[/red]"
            )
            return
            
        table = Table(
            show_footer=True,
            width=cli.config.get("width", None),
            pad_edge=True,
            box=None,
            show_edge=True
            )
        table.title = "[white]Profiles"
        table.add_column("A", style="red", justify="center", min_width=1)
        table.add_column("Name", style="white", justify="center", min_width=10)
        table.add_column("Path", style="white", justify="center", min_width=10)
        table.add_column("Size", style="white", justify="center", min_width=10)
        for profile in profile_details:
            #table.add_row("", profile[0], profile[1], profile[2])
            table.add_row("", *profile)
        bittensor.__console__.print(table)

    @staticmethod
    def check_config(config: "bittensor.config"):
        return config is not None        
    
    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        list_parser = parser.add_parser("list", help="""List profiles""")
        list_parser.set_defaults(func=ProfileListCommand.run)
        list_parser.add_argument(
            "--profile.path",
            type=str,
            default=defaults.profile.path,
            help="The path to the profile directory",
        )

class ProfilePrintCommand:
    """
    Executes the ``print`` command.

    This class provides functionality to print the content of a profile.
    """

    @staticmethod
    def run(cli):
        ProfilePrintCommand._run(cli)

    @staticmethod
    def _run(cli: "bittensor.cli"):
        config = cli.config
        profile_path = os.path.expanduser(config.profile.path)
        profile_name = config.profile.name
        if not os.path.isdir(profile_path):
            bittensor.__console__.print(f"[red]profile.path is not a directory:[/red][bold white] {profile_path}")
            return

        with open(f"{profile_path}{profile_name}", "r") as f:
            file_contents = f.read()

        profile_contents = yaml.safe_load(file_contents)
        ProfilePrintCommand.print_profile_contents(cli, profile_name, profile_contents)

    @staticmethod
    def print_profile_contents(cli, profile_name, profile_contents):
        flat_profile = flatdict.FlatDict(profile_contents, delimiter='.')
        table = Table(
            show_footer=True,
            width=cli.config.get("width", None),
            pad_edge=True,
            box=None,
            show_edge=True,
        )
        table.title = f"[white]Profile [bold white]{profile_name}"
        table.add_column("[overline white]PARAMETER", style="bold white", justify="left", min_width=10)
        table.add_column("[overline white]VALUE", style="green", justify="left", min_width=10)
        for key in flat_profile.keys():
            table.add_row(
                f"[bold white]{key}",
                f"[green]{flat_profile[key]}"
            )
        bittensor.__console__.print(table)

    @staticmethod
    def check_config(config: "bittensor.config"):
        return config is not None
        
    def add_args(parser: argparse.ArgumentParser):
        list_parser = parser.add_parser("print", help="""Print profile""")
        list_parser.set_defaults(func=ProfilePrintCommand.run)
        list_parser.add_argument(
            "--profile.name",
            type=str,
            help="The name of the profile",
        )
        list_parser.add_argument(
            "--profile.path",
            type=str,
            default=defaults.profile.path,
            help="The path to the profile directory",
        )

class ProfileUseCommand:
    """
    Executes the ``use`` command.

    This class provides functionality to change the active profile.
    """
    @staticmethod
    def run(cli):
        ProfileUseCommand._run(cli)

    @staticmethod
    def _run(cli: "bittensor.cli"):
        profile_name = cli.config.profile.name
        profile_path = cli.config.profile.path
        ProfileUseCommand.write_profile_to_disk(profile_name, profile_path)

    @staticmethod
    def write_profile_to_disk(profile_name, profile_directory):
        try:
            file_path = os.path.join(profile_directory, '.btcliprofile')
            with open(file_path, 'w') as file:
                file.write(profile_name)
            bittensor.__console__.print(f"[bold white]Profile set to {profile_name}.")
        except Exception as e:
            bittensor.__console__.print(f"[red]Error: Profile not set.[/red]\n[bold white]{e}")

    @staticmethod
    def check_config(config: "bittensor.config"):
        return config is not None

    def add_args(parser: argparse.ArgumentParser):
        list_parser = parser.add_parser("use", help="""Changes active profile""")
        list_parser.set_defaults(func=ProfileUseCommand.run)
        list_parser.add_argument(
            "--profile.name",
            type=str,
            help="The name of the profile",
        )
        list_parser.add_argument(
            "--profile.path",
            type=str,
            default=defaults.profile.path,
            help="The path to the profile directory",
        )