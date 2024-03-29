import sys
import asyncio
import random
import time
import importlib
import types
from typing import *
import shtab
import argparse
from injector import inject, singleton, Module

from btcli_interactive.overload.lazy_loader import LazyLoader, LazyModule, LazyProperty, LazyImportFinder, install_lazy_loader



ALIAS_TO_COMMAND = {
    "subnets": "subnets",
    "root": "root",
    "wallet": "wallet",
    "stake": "stake",
    "sudo": "sudo",
    "legacy": "legacy",
    "s": "subnets",
    "r": "root",
    "w": "wallet",
    "st": "stake",
    "su": "sudo",
    "l": "legacy",
    "subnet": "subnets",
    "roots": "root",
    "wallets": "wallet",
    "stakes": "stake",
    "sudos": "sudo",
    "i": "info",
    "info": "info",
}
COMMANDS = {
    "subnets": {
        "name": "subnets",
        "aliases": ["s", "subnet"],
        "help": "Commands for managing and viewing subnetworks.",
        "commands": {
            "list": "SubnetListCommand",
            "metagraph": "MetagraphCommand",
            "lock_cost": "SubnetLockCostCommand",
            "create": "RegisterSubnetworkCommand",
            "pow_register": "PowRegisterCommand",
            "register": "RegisterCommand",
            "hyperparameters": "SubnetHyperparamsCommand",
        },
    },
    "root": {
        "name": "root",
        "aliases": ["r", "roots"],
        "help": "Commands for managing and viewing the root network.",
        "commands": {
            "list": "RootList",
            "weights": "RootSetWeightsCommand",
            "get_weights": "RootGetWeightsCommand",
            "boost": "RootSetBoostCommand",
            "slash": "RootSetSlashCommand",
            "senate_vote": "VoteCommand",
            "senate": "SenateCommand",
            "register": "RootRegisterCommand",
            "proposals": "ProposalsCommand",
            "delegate": "DelegateStakeCommand",
            "undelegate": "DelegateUnstakeCommand",
            "my_delegates": "MyDelegatesCommand",
            "list_delegates": "ListDelegatesCommand",
            "nominate": "NominateCommand",
        },
    },
    "wallet": {
        "name": "wallet",
        "aliases": ["w", "wallets"],
        "help": "Commands for managing and viewing wallets.",
        "commands": {
            "list": "ListCommand",
            "overview": "OverviewCommand",
            "transfer": "TransferCommand",
            "inspect": "InspectCommand",
            "balance": "WalletBalanceCommand",
            "create": "WalletCreateCommand",
            "new_hotkey": "NewHotkeyCommand",
            "new_coldkey": "NewColdkeyCommand",
            "regen_coldkey": "RegenColdkeyCommand",
            "regen_coldkeypub": "RegenColdkeypubCommand",
            "regen_hotkey": "RegenHotkeyCommand",
            "faucet": "RunFaucetCommand",
            "update": "UpdateWalletCommand",
            "swap_hotkey": "SwapHotkeyCommand",
            "set_identity": "SetIdentityCommand",
            "get_identity": "GetIdentityCommand",
            "history": "GetWalletHistoryCommand",
        },
    },
    "stake": {
        "name": "stake",
        "aliases": ["st", "stakes"],
        "help": "Commands for staking and removing stake from hotkey accounts.",
        "commands": {
            "show": "StakeShow",
            "add": "StakeCommand",
            "remove": "UnStakeCommand",
        },
    },
    "sudo": {
        "name": "sudo",
        "aliases": ["su", "sudos"],
        "help": "Commands for subnet management",
        "commands": {
            # "dissolve": None,
            "set": "SubnetSudoCommand",
            "get": "SubnetGetHyperparamsCommand",
        },
    },
    "legacy": {
        "name": "legacy",
        "aliases": ["l"],
        "help": "Miscellaneous commands.",
        "commands": {
            "update": "UpdateCommand",
            "faucet": "RunFaucetCommand",
        },
    },
    "info": {
        "name": "info",
        "aliases": ["i"],
        "help": "Instructions for enabling autocompletion for the CLI.",
        "commands": {
            "autocomplete": "AutocompleteCommand",
        },
    },
}

class CLIErrorParser(argparse.ArgumentParser):
    """
    Custom ArgumentParser for better error messages.
    """

    def error(self, message):
        """
        This method is called when an error occurs. It prints a custom error message.
        """
        sys.stderr.write(f"Error: {message}\n")
        self.print_help()
        sys.exit(2)


class BittensorWSOptions(object):


    @staticmethod
    def __create_parser__() -> "argparse.ArgumentParser":
        """
        Creates the argument parser for the Bittensor CLI.

        Returns:
            argparse.ArgumentParser: An argument parser object for Bittensor CLI.
        """
        # Define the basic argument parser.
        parser = CLIErrorParser(
            description=f"bittensor cli v",
            usage="btcli <command> <command args>",
            add_help=True,
        )
        # Add shtab completion
        parser.add_argument(
            "--print-completion",
            choices=shtab.SUPPORTED_SHELLS,
            help="Print shell tab completion script",
        )
        # Add arguments for each sub-command.
        cmd_parsers = parser.add_subparsers(dest="command")
        # Add argument parsers for all available commands.
        for command in COMMANDS.values():
            if isinstance(command, dict):
                subcmd_parser = cmd_parsers.add_parser(
                    name=command["name"],
                    aliases=command["aliases"],
                    help=command["help"],
                )
                subparser = subcmd_parser.add_subparsers(
                    help=command["help"], dest="subcommand", required=True
                )

                for subcommand in command["commands"].values():
                    subcommand.add_args(subparser)
            else:
                command.add_args(cmd_parsers)

        return parser


if __name__ == "__main__":
    install_lazy_loader(
        [
            "websocket",
            "substrateinterface",
            "bittensor.subtensor.subtensor",
            "bittensor.metagraph.metagraph",
            "bittensor.cli.cli",
            "bittensor.chain_data.chain_data",
            "bittensor.wallet.wallet",
            "bittensor.cli.COMMANDS",
            "bittensor.axon.axon",
            "bittensor.dendrite.dendrite",
            "bittensor.tensor.tensor",
            "bittensor.commands.stake.StakeCommand",
            "bittensor.commands.stake.StakeShow",
            "bittensor.commands.unstake.UnStakeCommand",
            "bittensor.commands.overview.OverviewCommand",
            "bittensor.commands.misc.UpdateCommand",
            "bittensor.commands.misc.UpdateCommand",
            "bittensor.commands.list.ListCommand",
            "bittensor.commands.metagraph.MetagraphCommand",
            "bittensor.commands.inspect.InspectCommand",
            "bittensor.commands.transfer.TransferCommand",
            "bittensor.commands.wallets.GetWalletHistoryCommand",
            "bittensor.commands.wallets.WalletBalanceCommand",
            "bittensor.commands.wallets.WalletCreateCommand",
            "bittensor.commands.wallets.UpdateWalletCommand",
            "bittensor.commands.wallets.RegenHotkeyCommand",
            "bittensor.commands.wallets.RegenColdkeypubCommand",
            "bittensor.commands.wallets.RegenColdkeyCommand",
            "bittensor.commands.wallets.NewHotkeyCommand",
            "bittensor.commands.wallets.NewColdkeyCommand",
            "bittensor.commands.delegates.MyDelegatesCommand",
            "bittensor.commands.delegates.DelegateUnstakeCommand",
            "bittensor.commands.delegates.DelegateStakeCommand",
            "bittensor.commands.delegates.ListDelegatesCommand",
            "bittensor.commands.delegates.NominateCommand",
            "bittensor.commands.register.SwapHotkeyCommand",
            "bittensor.commands.register.RunFaucetCommand",
            "bittensor.commands.register.RegisterCommand",
            "bittensor.commands.register.PowRegisterCommand",
            "bittensor.senate.SenateCommand",
            "bittensor.senate.ProposalsCommand",
            "bittensor.senate.ShowVotesCommand",
            "bittensor.senate.SenateRegisterCommand",
            "bittensor.senate.SenateLeaveCommand",
            "bittensor.senate.VoteCommand",
            "bittensor.network.RegisterSubnetworkCommand",
            "bittensor.network.SubnetLockCostCommand",
            "bittensor.network.SubnetListCommand",
            "bittensor.network.SubnetSudoCommand",
            "bittensor.network.SubnetHyperparamsCommand",
            "bittensor.network.SubnetGetHyperparamsCommand",
            "bittensor.root.RootRegisterCommand",
            "bittensor.root.RootList",
            "bittensor.root.RootSetWeightsCommand",
            "bittensor.root.RootGetWeightsCommand",
            "bittensor.root.RootSetBoostCommand",
            "bittensor.root.RootSetSlashCommand",
            "bittensor.identity.GetIdentityCommand",
            "bittensor.identity.SetIdentityCommand",
            ]
        )
    asyncio.run(main())