# Standard Library
import argparse
import os
import yaml

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
        path = os.path.expanduser(config.profile["path"])
        profile_name = config.profile["name"]
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
        path = os.path.expanduser(cli.config.profile.path)
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            bittensor.__console__.print(
                f":cross_mark: [red]Failed to list profiles[/red]:[bold white] {e}"
            )
            return
        try:
            profiles = os.listdir(path)
        except Exception as e:
            bittensor.__console__.print(
                f":cross_mark: [red]Failed to list profiles[/red]:[bold white] {e}"
            )
            return
        if not profiles:
            bittensor.__console__.print(
                f":cross_mark: [red]No profiles found in {path}[/red]"
            )
            return
        profile_content = []
        for profile in profiles:
            #load profile
            try:
                with open(f"{path}{profile}", "r") as f:
                    config_content = f.read()
            except Exception as e:
                continue #Not a profile
            try:
                config = yaml.safe_load(config_content)
            except Exception as e:
                continue #Not a profile
            try:
                profile_content.append( (
                    " ",
                    str(config['profile']['name']),
                    str(config['subtensor']['network']),
                    str(config['netuid']),
                    )
                )
            except Exception as e:
                continue #not a proper profile
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
        table.add_column("Network", style="white", justify="center", min_width=10)
        table.add_column("Netuid", style="white", justify="center", min_width=10)
        for profile in profile_content:
            table.add_row(*profile)
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

class ProfileShowCommand:
    """
    Executes the ``show`` command.

    This class provides functionality to show the content of a profile.

    """

    @staticmethod
    def run(cli):
        ProfileShowCommand._run(cli)

    @staticmethod
    def _run(cli: "bittensor.cli"):
        config = cli.config.copy()
        path = os.path.expanduser(config.profile.path)
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            bittensor.__console__.print(
                f":cross_mark: [red]Failed to show profile[/red]:[bold white] {e}"
            )
            return
        try:
            profiles = os.listdir(path)
        except Exception as e:
            bittensor.__console__.print(
                f":cross_mark: [red]Failed to show profile[/red]:[bold white] {e}"
            )
            return
        if not profiles:
            bittensor.__console__.print(
                f":cross_mark: [red]No profiles found in {path}[/red]"
            )
            return
        with open(f"{path}{config.profile.name}", "r") as f:
            config_content = f.read()
        contents = yaml.safe_load(config_content)
        table = Table(
            show_footer=True,
            width=cli.config.get("width", None),
            pad_edge=True,
            box=None,
            show_edge=True,
        )
        table.title = f"[white]Profile [bold white]{config.profile.name}"
        table.add_column("[overline white]PARAMETERS", style="bold white", justify="left", min_width=10)
        table.add_column("[overline white]VALUES", style="green", justify="left", min_width=10)
        for key in contents.keys():
            if isinstance(contents[key], dict):
                for subkey in contents[key].keys():
                    table.add_row(
                        f"  [bold white]{key}.{subkey}",
                        f"[green]{contents[key][subkey]}"
                    )
                continue
            table.add_row(
                f"  [bold white]{key}",
                f"[green]{contents[key]}"
            )
        bittensor.__console__.print(table)

    @staticmethod
    def check_config(config: "bittensor.config"):
        return config is not None
        
    def add_args(parser: argparse.ArgumentParser):
        list_parser = parser.add_parser("show", help="""Show profile""")
        list_parser.set_defaults(func=ProfileShowCommand.run)
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